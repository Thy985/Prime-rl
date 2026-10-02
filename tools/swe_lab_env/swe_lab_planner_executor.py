"""Harness D: `bash` + `edit` spent through a plan -> execute -> feedback allocation.

Why this harness exists. Harness A solves every tier of the ladder 8/8; only a binding
turn budget (`max_turns = 4`) produces a graded frontier -- 100 / 100 / 12.5 / 75 /
12.5%. H_D runs the same model, taskset, tools, runtime and cap, and changes only how
that allowance is spent: a fixed allocation across three phases instead of a free
allocation across one loop.

  plan      1 model call   bash only, write commands refused, no edit tool
  execute   2 model calls  bash + edit
  feedback  the rest       bash + edit

The allocation is the intervention, and it is why this is a harness program rather than
a system-prompt hint. The first version let each phase run until the model replied with
text, as the stock loop ends an episode; the smoke episode then spent all four turns of
its budget inside the planning phase (pytest, two file reads, a 1190-character plan) and
was stopped at max_turns with reward 0.0, never reaching execute. Under a binding budget
an unbounded phase is not a phase.

Predictions, recorded before the first full run (the smoke episode is not evidence
either way -- one episode, easiest tier):
  P+  solve rises on tier3/tier5 if those failures are "acted without a plan";
  P-  solve falls, because turn 1 cannot write and execution gets two turns where the
      free-form loop gets up to four;
  P0  solve holds and only the tool mix moves (inspect-heavy turn 1, edit-heavy middle)
      -- a phase allocation is then not the structure the failures need.

Not a fork: verifiers' own bundler concatenates the stock chat program's modules and
`swe_lab_planner_program` is appended in place of core's entry point, so the tools, the
tool gate, compaction and the retry policy stay the framework's.
"""

from __future__ import annotations

import inspect

import swe_lab_planner_program
from verifiers.v1.harnesses.bash.harness import (
    BASH_SYSTEM_PROMPT,
    EDIT_SYSTEM_PROMPT,
    BashHarness,
)
from verifiers.v1.harnesses.utils import compaction, core, mcp
from verifiers.v1.harnesses.utils.launch import (
    CHAT_PROGRAM,
    bundle_program,
    launch_chat_program,
)

__all__ = ["BashPlannerExecutorHarness"]

ENTRY_POINT = 'if __name__ == "__main__":'

PHASE_PROTOCOL = (
    "\n\nYou work in three phases, and the harness allocates the turns:\n"
    "1 PLAN -- one turn, bash only, commands that change the repository are refused: "
    "find the defect and state the change to make.\n"
    "2 EXECUTE -- two turns with bash and edit: apply the repair to the files on disk.\n"
    "3 FEEDBACK -- the remaining turns: re-run the failing suite, repair what is still "
    "broken, report the result.\n"
    "The turn budget is counted across all three phases."
)

_BUNDLED = bundle_program(CHAT_PROGRAM, mcp, compaction, core)
if ENTRY_POINT not in _BUNDLED:
    raise RuntimeError(
        "verifiers' bundled chat program no longer ends with "
        f"{ENTRY_POINT!r}; swe-lab Harness D cannot replace its entry point"
    )
PROGRAM_SOURCE = _BUNDLED.rsplit(ENTRY_POINT, 1)[0] + inspect.getsource(
    swe_lab_planner_program
)


class BashPlannerExecutorHarness(BashHarness):
    """`bash` + `edit`, spent through a fixed plan/execute/feedback allocation."""

    def resolve_prompt(self, task):
        system, prompt = super().resolve_prompt(task)
        return (system or "") + PHASE_PROTOCOL, prompt

    async def setup(self, runtime) -> None:
        await runtime.prepare_uv_script(PROGRAM_SOURCE, self.config.resolved_env)

    async def launch(
        self,
        ctx,
        trace,
        runtime,
        endpoint,
        secret,
        mcp_urls,
        data,
        tool_interception_url=None,
    ):
        if self.config.search:
            raise ValueError(
                "harness 'swe-lab-planner-executor' does not support the search tool; "
                "use 'bash' for that condition"
            )
        system_prompt, prompt = self.resolve_prompt(data)
        fragments = [BASH_SYSTEM_PROMPT]
        if self.config.edit:
            fragments.append(EDIT_SYSTEM_PROMPT)
        system_prompt = "\n\n".join(p for p in (" ".join(fragments), system_prompt) if p)
        args = ["--bash"]
        if tool_interception_url:
            args.append(f"--tool-interception-url={tool_interception_url}")
        if self.config.compaction is not None:
            args.append("--compaction")
            if self.config.compaction.summarize_at_tokens is not None:
                args.append(
                    f"--summarize-at-tokens={self.config.compaction.summarize_at_tokens}"
                )
        if self.config.edit:
            args.append("--edit")
        return await launch_chat_program(
            PROGRAM_SOURCE,
            self.config,
            ctx,
            trace,
            runtime,
            endpoint,
            secret,
            mcp_urls,
            system_prompt,
            prompt,
            extra_args=args,
            env={**self.config.resolved_env},
            activate=False,
        )