"""Harness ADAPT: a deterministic affordance scheduler over the turn budget.

This module is not executed where it is imported: `swe_lab_adaptive_executor`
appends its source to verifiers' own bundled chat program, so the names it uses
-- BASH_TOOL, EDIT_TOOL, SEARCH_TOOL, chat, run_bash, run_edit, run_search,
gate_tool_call, bound_tool_message, estimated_tokens, compactable, Compactor,
discover_threshold, connect_mcp, call_mcp, parse_args -- are the framework's,
not a fork of them.

The controller owns only the per-turn tool list, decided from the trajectory so
far. There are no phase prompts and no protocol text: the model sees the neutral
system prompt, the task, and whatever tools the current state happens to offer,
exactly like H_G -- and unlike H_G the schedule is not fixed in advance, the
program observes the calls and moves between states as it watches them.

  RECON   [bash]             edit is not offered; tree-changing bash is refused
  EXECUTE [bash, edit]       edit is unlocked
  VERIFY  [bash]             edit is removed again: with the budget nearly
                             spent, the turn exists to run the suite, and with
                             edit absent the only way to act on the failing
                             tests is to run them

Deterministic transitions, decided from observed calls only:

  RECON -> EXECUTE when
    - two consecutive turns made only inspection calls (the same inspection
      pattern repeating: the agent is re-reading instead of changing), or
    - the remaining budget is <= 2 (unlock under budget pressure)
  EXECUTE -> VERIFY when
    - an edit was made, no test has ever run, and the remaining budget is <= 1
      (allocate a verification turn before the budget closes)

A text reply ends the episode, as in the stock loop and H_A. The budget is read
from SWE_LAB_BUDGET (default 4) and must match the config's `max_turns`; the
framework itself enforces the cap, this value only feeds the scheduler.
"""

import asyncio
import json
import os
import re
from contextlib import AsyncExitStack
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
from openai import AsyncOpenAI

if TYPE_CHECKING:
    from verifiers.v1.harnesses.utils.compaction import (
        Compactor,
        bound_tool_message,
        compactable,
        discover_threshold,
        estimated_tokens,
    )
    from verifiers.v1.harnesses.utils.core import (
        BASH_TOOL,
        EDIT_TOOL,
        SEARCH_TOOL,
        gate_tool_call,
        parse_args,
        run_bash,
        run_edit,
        run_search,
    )
    from verifiers.v1.harnesses.utils.mcp import call_mcp, connect_mcp

# The same coarse read-only test the planner uses: commands that obviously change
# the tree are refused in RECON so that state cannot silently leave recon.
WRITE_COMMAND = re.compile(
    r"(?:^|[;&|])\s*(?:rm|mv|cp|tee|truncate|dd|touch|mkdir|patch|sed\s+-i|"
    r"git\s+(?:apply|checkout|restore|clean))\b"
    r"|>{1,2}(?!&)\s*(?!/dev/null\b)\S"
)

INSPECT_RE = re.compile(
    r"^\s*(?:cat|ls|head|tail|grep|find|sed|wc|file|awk|less|diff|"
    r"git\s+(?:log|status|diff|show))\b"
)
TEST_RE = re.compile(
    r"\bpytest\b|\bunittest\b|runtests\.py\b|manage\.py\s+test"
)


def command_kind(command):
    """One action kind per bash command: test > write > inspect > other."""
    text = command or ""
    if TEST_RE.search(text):
        return "test"
    if WRITE_COMMAND.search(text):
        return "write"
    if INSPECT_RE.match(text):
        return "inspect"
    return "other"


def looks_like_write(command):
    return bool(WRITE_COMMAND.search(command or ""))


def state_tools(state, args):
    """The tools advertised in `state`: edit exists only in EXECUTE."""
    tools = [BASH_TOOL] if args.bash else []
    if args.edit and state == "EXECUTE":
        tools.append(EDIT_TOOL)
    if args.search:
        tools.append(SEARCH_TOOL)
    return tools


def initial_messages(args, initial):
    messages = [{"role": "system", "content": args.system_prompt}] if args.system_prompt else []
    if initial:
        messages.extend(initial)
    elif args.prompt:
        messages.append({"role": "user", "content": args.prompt})
    return messages


async def run_turn(args, client, model, messages, tools, dispatch, servers, tool_client, read_only):
    """One model call plus the framework's tool dispatch.

    Returns (messages, text_reply, kinds): text_reply is non-empty when the model
    ended the episode with prose; kinds are the action kinds of the calls that
    actually ran (denied or refused calls are skipped, they mutated nothing).
    """
    compactor = Compactor(client, model, tools, args.compaction, args.summarize_at_tokens)
    if compactor.enabled and compactor.threshold is None:
        compactor.threshold = await discover_threshold(client, model)
    compactor.note_good(messages)
    completion, messages = await compactor.complete(messages)
    message = completion.choices[0].message
    messages.append(message.model_dump(exclude_none=True))
    if not message.tool_calls:
        return messages, (message.content or "").strip(), []
    tool_result_tokens = 0
    kinds = []
    for call in message.tool_calls:
        name = call.function.name
        tool_message = {"role": "tool", "tool_call_id": call.id, "content": "", "name": name}
        if args.tool_interception_url:
            decision = await gate_tool_call(tool_client, args.tool_interception_url, args.api_key, call)
            if decision["action"] == "deny":
                tool_message = bound_tool_message(decision["message"])
                messages.append(tool_message)
                tool_result_tokens += estimated_tokens(str(tool_message.get("content", "")))
                continue
        try:
            tool_args = json.loads(call.function.arguments or "{}")
        except json.JSONDecodeError as error:
            content = "error: invalid JSON in tool arguments (%s); resend the call with valid JSON" % error
        else:
            if not isinstance(tool_args, dict):
                content = "error: tool arguments must be a JSON object, got %s" % type(tool_args).__name__
            elif read_only and name == "bash" and looks_like_write(tool_args.get("command", "")):
                content = "error: writes are not allowed in this turn"
            elif name in dispatch:
                content = await call_mcp(servers, dispatch, name, tool_args)
            elif name == "bash" and args.bash:
                content = await asyncio.to_thread(run_bash, tool_args.get("command", ""))
            elif name == "edit" and args.edit:
                content = await asyncio.to_thread(
                    run_edit, tool_args.get("path"), tool_args.get("old_str"), tool_args.get("new_str")
                )
            elif name == "search" and args.search:
                content = await asyncio.to_thread(
                    run_search, tool_args.get("query", ""), args.serper_key, tool_args.get("num_results", 5)
                )
            else:
                content = "error: unknown tool %r" % name
        if name == "bash":
            kinds.append(command_kind(tool_args.get("command", "")))
        elif name == "edit":
            kinds.append("edit")
        else:
            kinds.append("other")
        tool_message["content"] = content
        tool_message = bound_tool_message(tool_message)
        messages.append(tool_message)
        tool_result_tokens += estimated_tokens(str(tool_message["content"]))
    if compactor.reached(completion, tool_result_tokens) and compactable(messages):
        messages = await compactor.compact(messages)
    return messages, "", kinds


async def adaptive_main():
    args = parse_args()
    initial = []
    if args.initial_messages_file:
        path = Path(args.initial_messages_file)
        payload = path.read_bytes()
        path.unlink()
        initial = json.loads(payload)
    client = AsyncOpenAI(
        base_url=args.base_url,
        api_key=args.api_key,
        timeout=httpx.Timeout(600.0 if args.bash else None, connect=5.0),
    )
    tool_client = (
        httpx.AsyncClient(timeout=httpx.Timeout(None, connect=5.0))
        if args.tool_interception_url
        else None
    )
    config = json.loads(args.mcp_config or "{}")
    reserved = {"bash"} if args.bash else set()
    if args.edit:
        reserved.add("edit")
    if args.search:
        reserved.add("search")
    async with AsyncExitStack() as stack:
        if config.get("mcpServers"):
            mcp_tools, dispatch, servers = await asyncio.wait_for(
                connect_mcp(config, stack, reserved), timeout=None if args.bash else 60
            )
        else:
            mcp_tools, dispatch, servers = [], {}, {}
        messages = initial_messages(args, initial)
        budget = int(os.environ.get("SWE_LAB_BUDGET", "4") or "4")
        state = "RECON"
        calls = 0
        edit_seen = False
        tests_run = False
        prev_inspect_only = False
        while True:
            if calls >= budget:
                break
            messages, text, kinds = await run_turn(
                args, client, args.model, messages, state_tools(state, args) + mcp_tools,
                dispatch, servers, tool_client, read_only=(state == "RECON"),
            )
            calls += 1
            if text:
                break
            for kind in kinds:
                if kind == "edit":
                    edit_seen = True
                elif kind == "test":
                    tests_run = True
            remaining = budget - calls
            inspect_only = bool(kinds) and all(k == "inspect" for k in kinds)
            if state == "RECON":
                if (inspect_only and prev_inspect_only) or remaining <= 2:
                    state = "EXECUTE"
            elif state == "EXECUTE":
                if edit_seen and not tests_run and remaining <= 1:
                    state = "VERIFY"
            prev_inspect_only = inspect_only
    if tool_client is not None:
        await tool_client.aclose()


if __name__ == "__main__":
    asyncio.run(adaptive_main())