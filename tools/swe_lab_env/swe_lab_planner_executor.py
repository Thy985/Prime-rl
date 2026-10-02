"""Harness D: a staged, phase-gated allocation of a binding turn budget.

Harness A solves every tier of the ladder 8/8; only a binding turn budget
(`max_turns = 4`) produces a graded frontier -- 100 / 100 / 12.5 / 75 / 12.5%. H_D runs
the same model, taskset, tools, runtime and cap, and changes only how that allowance is
spent: a fixed allocation across three phases instead of a free allocation across one
loop.

  plan (read-only recon)   1 model call   bash only, write commands refused, no edit tool
  execute                  2 model calls  bash + edit
  feedback (verify)        the rest       bash + edit

It is a *staged execution* harness, not a planner/executor: across 120 episodes no model
ever wrote a plan in the recon turn (0/120) -- given one turn it always inspected -- so
what is actually tested is whether redistributing a fixed budget across read-only recon,
execution and verification beats spending it freely. The "planner" name is retired from
the framing; the harness id and module names are kept stable so the recorded H_A / H_D /
H_E runs stay reproducible.

The allocation is the intervention, and it is why this is a harness program rather than
a system-prompt hint. The first version let each phase run until the model replied with
text, as the stock loop ends an episode; the smoke episode then spent all four turns of
its budget inside the recon phase (pytest, two file reads, a 1190-character plan) and was
stopped at max_turns with reward 0.0, never reaching execute. Under a binding budget an
unbounded phase is not a phase.

Predictions, recorded before the first full run (the smoke episode is not evidence
either way -- one episode, easiest tier):
  P+  solve rises on tier3/tier5 if those failures are "acted without first looking";
  P-  solve falls, because turn 1 cannot write and execution gets two turns where the
      free-form loop gets up to four;
  P0  solve holds and only the tool mix moves (inspect-heavy turn 1, edit-heavy middle)
      -- a phase allocation is then not the structure the failures need.
  Outcome: tier3 rose (21% -> 58%, non-overlapping) and the H_E ablation decomposed the
  gain into a verify-turn and a recon-turn component, roughly additive -- P0 did not
  hold, and the value is a redistribution of action opportunity, not added planning.

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


def _phase_protocol(env):
    """The system-prompt description of the phases. The default is the verbatim text the
    recorded Harness D runs used; a custom `SWE_LAB_PHASES` rebuilds it for the chosen
    phases so the prompt never describes a phase the program will skip."""
    if env.get("SWE_LAB_QUIET"):
        return ""
    raw = env.get("SWE_LAB_PHASES")
    if not raw:
        return PHASE_PROTOCOL
    parts = [p.strip() for p in raw.split(",")]
    caps = []
    for i in range(3):
        if i < len(parts) and parts[i] != "":
            caps.append(int(parts[i]))
        else:
            caps.append(None)
    names = ("plan", "execute", "feedback")
    active = [(names[i], caps[i]) for i in range(3) if caps[i] != 0]
    lines = ["", "", "You work in %d phases, and the harness allocates the turns:" % len(active)]
    for idx, (name, cap) in enumerate(active, 1):
        if name == "plan":
            desc = "one turn, bash only, commands that change the repository are refused: find the defect and state the change to make."
        elif name == "execute":
            n = cap if cap is not None else "the remaining"
            desc = "%s turns with bash and edit: apply the repair to the files on disk." % n
        else:
            desc = "the remaining turns: re-run the failing suite, repair what is still broken, report the result."
        lines.append("%d %s -- %s" % (idx, name.upper(), desc))
    lines.append("The turn budget is counted across all %d phases." % len(active))
    return "\n".join(lines)

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
        return (system or "") + _phase_protocol(self.config.env), prompt

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