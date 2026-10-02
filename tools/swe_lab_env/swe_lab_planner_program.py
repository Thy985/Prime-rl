"""The Harness D runtime program: a staged recon -> execute -> verify allocation.

This module is not executed where it is imported. `swe_lab_planner_executor` appends
its source to verifiers' own bundled chat program, so the names it uses -- BASH_TOOL,
EDIT_TOOL, chat, run_bash, run_edit, gate_tool_call, bound_tool_message,
estimated_tokens, compactable, Compactor, discover_threshold, connect_mcp, call_mcp,
parse_args -- are the framework's, not a fork of them.

That contract costs two rules: no `from __future__ import annotations` (it would not
be the first statement of the bundled script) and no import of verifiers.

The turn cap is not enforced here: verifiers refuses the turn that would exceed
`max_turns`, the program dies on that refusal, and the harness boundary treats it as
the clean budget stop it is. What the program does own is the ALLOCATION of a fixed
allowance across the three phases:

  plan (read-only recon)   1 model call   bash, no edit tool, write commands refused
  execute                  2 model calls  bash + edit
  feedback (verify)        the rest       bash + edit

It is staged execution, not planning: across 120 episodes no model ever wrote a plan in
the recon turn (0/120) -- given one turn it always inspected instead. "Planner" is
therefore retired from the framing; what this tests is the redistribution of a binding
budget across recon, execution and verification. The allocation is not decoration. The
first version let each phase run until the model replied with text, exactly as the stock
loop ends an episode; the smoke episode then spent all four turns of a 4-turn budget
inside the recon phase (pytest, then two file reads, then a 1190-character plan) and was
stopped at max_turns with reward 0.0, never reaching execute. An unbounded phase is not
a phase under a binding budget, so each early phase gets a call allowance and closes when
it is spent, even if the model would have kept talking. The final phase is uncapped by
the program and ends at the framework's own limit.

The allowance is read from SWE_LAB_PHASES at run time ("plan,execute,feedback"; an empty
field or a missing trailing field means "until the framework stops us", 0 skips the
phase). The default is the recorded Harness D allocation; "0,3," is the H_E control,
which removes the recon turn and gives its call to execute.
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
    # These are defined by the bundled chat program this module is appended to, so the
    # declarations are annotation-time only: nothing is imported, either in the host
    # that imports this module or in the script the harness generates.
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

# Turn allowance per phase, read from SWE_LAB_PHASES as "plan,execute,feedback": an
# empty field (or a missing trailing one) means "until the framework stops us", 0 skips
# the phase. The default is the recorded Harness D allocation; "0,3," is the H_E control.
DEFAULT_ALLOCATION = "1,2,"


def parse_allocation(raw=DEFAULT_ALLOCATION):
    parts = [p.strip() for p in raw.split(",")]
    caps = []
    for i in range(3):
        if i < len(parts) and parts[i] != "":
            caps.append(int(parts[i]))
        else:
            caps.append(None)
    names = ("plan", "execute", "feedback")
    return [(names[i], caps[i]) for i in range(3) if caps[i] != 0]

# Deliberately coarse: the planning phase is read-only for commands that obviously
# change the tree. It does not police bash; it stops the plan phase from silently
# becoming the execution phase, which is the whole difference being measured.
WRITE_COMMAND = re.compile(
    r"(?:^|[;&|])\s*(?:rm|mv|cp|tee|truncate|dd|touch|mkdir|patch|sed\s+-i|"
    r"git\s+(?:apply|checkout|restore|clean))\b"
    r"|>{1,2}(?!&)\s*(?!/dev/null\b)\S"
)

# The 'plan' phase is read-only recon in practice (0/120 wrote a plan); the label is
# kept as the stable phase identifier, not as a claim about planning behaviour.
PLAN_INSTRUCTION = (
    "PHASE 1 of 3 -- PLAN. This is your only planning turn: one turn to inspect and "
    "decide, so spend it on the repository rather than on restating the task. Use bash "
    "to find the defect; commands that change the repository are refused in this phase "
    "and the edit tool is not available. Also reply with text at the end of this turn "
    "if you can: the change to make in each file. The next phase applies it."
)

EXECUTE_INSTRUCTION = (
    "PHASE 2 of 3 -- EXECUTE. Two turns to make the repair.\n"
    "What the planning turn produced:\n"
    "---\n"
    "{plan}\n"
    "---\n"
    "Apply it now: change the files on disk with bash and edit. Do not restate the change "
    "instead of making it. Reply with text once the edits are in place."
)

FEEDBACK_INSTRUCTION = (
    "PHASE 3 of 3 -- FEEDBACK. Re-run the failing tests and read the output. If they "
    "still fail, repair what remains and run them once more. Reply with text stating the "
    "final result of the suite."
)


def phase_instruction(phase, plan, had_plan, idx, total, turns):
    """The phase prompt. The default allocation uses the verbatim strings above (the ones
    the recorded Harness D runs used); a custom `SWE_LAB_PHASES` rebuilds the numbering,
    the turn count and the plan block for whichever phases are actually run."""
    if "SWE_LAB_PHASES" not in os.environ:
        if phase == "plan":
            return PLAN_INSTRUCTION
        if phase == "execute":
            stated = plan.strip() or (
                "(the planning turn ended without a written plan; act on what it inspected)"
            )
            return EXECUTE_INSTRUCTION.format(plan=stated)
        return FEEDBACK_INSTRUCTION
    if phase == "plan":
        return (
            "PHASE %d of %d -- PLAN. This is your only planning turn: one turn to inspect and "
            "decide, so spend it on the repository rather than on restating the task. Use bash "
            "to find the defect; commands that change the repository are refused in this phase "
            "and the edit tool is not available. Also reply with text at the end of this turn "
            "if you can: the change to make in each file. The next phase applies it." % (idx, total)
        )
    if phase == "execute":
        plan_block = ""
        if had_plan:
            stated = plan.strip() or (
                "(the planning turn ended without a written plan; act on what it inspected)"
            )
            plan_block = "What the planning turn produced:\n---\n%s\n---\n" % stated
        return (
            "PHASE %d of %d -- EXECUTE. %d turns to make the repair.\n"
            "%s"
            "Apply it now: change the files on disk with bash and edit. Do not restate the change "
            "instead of making it. Reply with text once the edits are in place."
            % (idx, total, turns, plan_block)
        )
    return (
        "PHASE %d of %d -- FEEDBACK. Re-run the failing tests and read the output. If they "
        "still fail, repair what remains and run them once more. Reply with text stating the "
        "final result of the suite." % (idx, total)
    )


def looks_like_write(command):
    return bool(WRITE_COMMAND.search(command or ""))


def phase_tools(phase, args):
    """The tools advertised in `phase`: the plan phase gets no edit tool."""
    tools = [BASH_TOOL] if args.bash else []
    if args.edit and phase != "plan":
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


async def run_phase(args, client, model, messages, tools, dispatch, servers, tool_client, read_only, max_calls, quiet):
    """Run one phase, mirroring the stock loop's tool dispatch and compaction.

    Returns the conversation and the phase's closing text reply (empty when the phase
    closed because its call allowance ran out, not because the model finished).
    """
    compactor = Compactor(client, model, tools, args.compaction, args.summarize_at_tokens)
    if compactor.enabled and compactor.threshold is None:
        compactor.threshold = await discover_threshold(client, model)
    compactor.note_good(messages)
    calls = 0
    while True:
        completion, messages = await compactor.complete(messages)
        calls += 1
        message = completion.choices[0].message
        messages.append(message.model_dump(exclude_none=True))
        if not message.tool_calls:
            return messages, (message.content or "").strip()
        tool_result_tokens = 0
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
                    if quiet:
                        content = "error: writes are not allowed in this turn"
                    else:
                        content = (
                            "error: this is the planning turn and that command changes the repository; "
                            "inspect the code and describe the change instead -- the execute phase applies it"
                        )
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
            tool_message["content"] = content
            tool_message = bound_tool_message(tool_message)
            messages.append(tool_message)
            tool_result_tokens += estimated_tokens(str(tool_message["content"]))
        if compactor.reached(completion, tool_result_tokens) and compactable(messages):
            messages = await compactor.compact(messages)
        if max_calls is not None and calls >= max_calls:
            return messages, ""


async def phased_main():
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
        allocation = parse_allocation(os.environ.get("SWE_LAB_PHASES", DEFAULT_ALLOCATION))
        total = len(allocation)
        had_plan = any(name == "plan" for name, _ in allocation)
        quiet = bool(os.environ.get("SWE_LAB_QUIET"))
        plan = ""
        for idx, (phase, max_calls) in enumerate(allocation, 1):
            tools = phase_tools(phase, args) + mcp_tools
            turns = max_calls if max_calls is not None else 0
            if not quiet:
                messages.append({"role": "user", "content": phase_instruction(phase, plan, had_plan, idx, total, turns)})
            messages, reply = await run_phase(
                args, client, args.model, messages, tools, dispatch, servers, tool_client,
                read_only=(phase == "plan"), max_calls=max_calls, quiet=quiet,
            )
            if phase == "plan":
                plan = reply
    if tool_client is not None:
        await tool_client.aclose()


if __name__ == "__main__":
    asyncio.run(phased_main())