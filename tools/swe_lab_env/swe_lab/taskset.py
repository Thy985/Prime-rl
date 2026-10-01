"""swe-lab: single-turn code repair scored by an executing verifier.

The model is shown a small two-defect repository and the failing suite, and must
reply with the complete corrected `calculator.py` in one fenced block. The reward
is not a proxy over text: the proposed file is written into a throwaway copy of
the fixture, the suite is executed, and the audited verdict from
`tools/swe_lab/terrain.py` is turned into a reward. A reply that modifies or
deletes tests scores zero, a partial fix earns partial credit, and a regression
scores zero -- the properties established by the terrain audit before any
training.

Needs no container: the `null` harness is a single-turn chat loop and the
`subprocess` runtime executes the suite on the host.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import verifiers.v1 as vf

# terrain.py and contract.py live in tools/swe_lab and are not an installed package.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "swe_lab"))

import terrain as terrain_verifier

CODE_BLOCK = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)

SYSTEM = (
    "You are a careful Python engineer. Reply with the complete corrected file in "
    "a single fenced code block and change nothing else."
)


def build_prompt() -> str:
    calc = (terrain_verifier.FIXTURE / "calculator.py").read_text()
    tests = (terrain_verifier.FIXTURE / "test_calculator.py").read_text()
    return (
        "This small repository has a failing test suite.\n\n"
        "--- calculator.py ---\n" + calc + "\n"
        "--- test_calculator.py ---\n" + tests + "\n"
        "Running `python -m pytest` reports these failures:\n  "
        + "\n  ".join(terrain_verifier.FAILING)
        + "\n\nFix calculator.py so that every test passes. Do not modify the tests. "
        "Reply with the complete corrected contents of calculator.py in one "
        "```python fenced block."
    )


class SweLabData(vf.TaskData):
    target_tests: list[str] = []
    """Baseline-failing tests the repair must fix."""


class SweLabTask(vf.Task[SweLabData]):
    def __init__(self, data, config=None):
        super().__init__(data, config)
        self._baseline = terrain_verifier.baseline_outcome()

    @vf.stop
    async def single_turn(self, trace: vf.Trace) -> bool:
        """One answer, like reverse-text: refuse a second turn."""
        return trace.num_turns >= 1

    def _verdict(self, reply: str):
        blocks = CODE_BLOCK.findall(reply or "")
        if not blocks:
            return None
        # The full file is the largest block; a model that emits fragments is scored on what it gave.
        proposed = max(blocks, key=len)
        return terrain_verifier.evaluate({"calculator.py": proposed}, self._baseline)

    @vf.reward(weight=1.0)
    async def target_fix_fraction(self, trace: vf.Trace) -> float:
        verdict = self._verdict(trace.last_reply)
        if verdict is None:
            return 0.0
        return terrain_verifier.REWARDS["target_fix_fraction"](verdict)

    @vf.reward(weight=0.0)
    async def shaped(self, trace: vf.Trace) -> float:
        """Recorded alongside the primary reward so the audit travels with the trace."""
        verdict = self._verdict(trace.last_reply)
        if verdict is None:
            return 0.0
        return terrain_verifier.REWARDS["shaped"](verdict)


class SweLabConfig(vf.TasksetConfig):
    pass


class SweLabTaskset(vf.Taskset[SweLabTask, SweLabConfig]):
    def load(self) -> list[SweLabTask]:
        prompt = build_prompt()
        return [
            SweLabTask(
                SweLabData(
                    idx=0,
                    name="swe-lab-2defect",
                    prompt=prompt,
                    system_prompt=SYSTEM,
                    target_tests=list(terrain_verifier.FAILING),
                ),
                self.config.task,
            )
        ]