"""Harness C: a bash harness that states the completion requirement as a constraint.

Phase 3.6 found that every failure in the bash-only cohort ended WITHOUT writing a
single file: the agent inspected the repository, ran a test or two, and stopped
after 2.3 tool calls on average. That is not a wrong patch, it is no patch, and the
two call for different interventions.

This harness keeps the same execution loop, the same runtime and the same tools as
`bash`. It changes only what the harness itself owns -- the system prompt -- to make
the completion condition explicit: the file on disk must actually change, and the
suite must be re-run before finishing. That makes the hypothesis falsifiable against
the identical condition, with `no-write` as the measured axis.

Because `BashHarness.APPENDS_SYSTEM_PROMPT` is True, the prompt returned here is
emitted as a system message rather than folded into the user prompt.
"""

from __future__ import annotations

from verifiers.v1.harnesses.bash.harness import BASH_SYSTEM_PROMPT, BashHarness

__all__ = ["BashPatchFirstHarness"]

COMPLETION_REQUIREMENT = (
    " You are not finished until the file on disk has actually been changed. "
    "Explaining the defect, or printing a corrected file in your reply, is not a fix: "
    "apply the change with your tools. Before you finish, re-run the failing test "
    "suite and confirm from its output that it passes."
)


class BashPatchFirstHarness(BashHarness):
    """`bash`, with the completion condition made explicit in the system prompt."""

    def resolve_prompt(self, task):
        system, prompt = super().resolve_prompt(task)
        if system is None:
            system = BASH_SYSTEM_PROMPT
        return system + COMPLETION_REQUIREMENT, prompt