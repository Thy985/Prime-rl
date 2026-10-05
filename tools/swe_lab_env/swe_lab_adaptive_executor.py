"""Harness ADAPT: the same tools, runtime and budget as `bash` and Harness D, spent
through a deterministic affordance scheduler instead of a fixed allocation.

Harness D redistributes a binding budget across plan/execute/feedback with a fixed
schedule. This harness keeps the recon -> execute -> verify structure but decides
the per-turn tool list from the observed trajectory: RECON ends on repeated
inspection or budget pressure, VERIFY is allocated on the last turn when an edit
exists but no test ever ran. No phase prompts and no protocol text -- the only
signal is which tools the current turn offers.

The scheduler itself lives in `swe_lab_adaptive_program`, appended to the
framework's bundled chat program in place of its entry point, exactly as the
planner executor does. The harness id is `swe-lab-adaptive-executor` (module
`swe_lab_adaptive_executor`, found via PYTHONPATH=tools/swe_lab_env).
"""

from __future__ import annotations

import inspect

import swe_lab_adaptive
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

__all__ = ["BashAdaptiveHarness"]

ENTRY_POINT = 'if __name__ == "__main__":'

_BUNDLED = bundle_program(CHAT_PROGRAM, mcp, compaction, core)
if ENTRY_POINT not in _BUNDLED:
    raise RuntimeError(
        "verifiers' bundled chat program no longer ends with "
        f"{ENTRY_POINT!r}; swe-lab Harness ADAPT cannot replace its entry point"
    )
PROGRAM_SOURCE = _BUNDLED.rsplit(ENTRY_POINT, 1)[0] + inspect.getsource(
    swe_lab_adaptive
)


class BashAdaptiveHarness(BashHarness):
    """`bash` + `edit`, scheduled turn by turn from the observed trajectory."""

    def resolve_prompt(self, task):
        # No phase protocol: the neutral system prompt is the whole system text.
        return super().resolve_prompt(task)

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
                "harness 'swe-lab-adaptive-executor' does not support the search tool; "
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