"""swe-lab: the tiered code-repair taskset, scored by an executing verifier.

One task per difficulty tier (see tools/swe_lab/ladder.py). The model is shown the
tier's repository and its failing suite, and must reply with the corrected
contents of the file(s) it changes, one fenced block per file preceded by a
`### FILE: <path>` line.

The reward is not a proxy over text. The proposed file contents are written into a
throwaway copy of the tier's repository, the suite is executed, and the audited
verdict from tools/swe_lab/terrain.py becomes the reward:
`target_fix_fraction` = fraction of the tier's target tests actually fixed, gated
to zero when a test file was modified or a previously passing test regressed.
`shaped` is recorded alongside at weight 0.

No container is needed: the `null` harness is a single-turn chat loop and the
`subprocess` runtime runs the suite on the host.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import verifiers.v1 as vf

SWE_LAB = Path(__file__).resolve().parents[2] / "swe_lab"
sys.path.insert(0, str(SWE_LAB))

import ladder as ladder_defs
import terrain as terrain_verifier

FILE_MARKER = re.compile(r"^###\s*FILE:\s*(\S+)\s*$", re.MULTILINE)
CODE_BLOCK = re.compile(r"```(?:python)?\s*\n(.*?)```", re.DOTALL)

SYSTEM = (
    "You are a careful Python engineer. Reply with the complete corrected contents "
    "of every file you change, one fenced code block per file, each preceded by a "
    "line `### FILE: <relative path>`. Change nothing else."
)

_BASELINES: dict[str, dict] = {}


def _baseline(tier_id: str, files: dict) -> dict:
    """Baseline verdict for a tier, computed once and cached."""
    if tier_id in _BASELINES:
        return _BASELINES[tier_id]
    with TemporaryDirectory() as tmp:
        tree = Path(tmp) / "repo"
        for rel, content in files.items():
            path = tree / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
        _, _, per_test = terrain_verifier.run_repo(tree)
    baseline = {
        "per_test": per_test,
        "passing": [t for t, v in per_test.items() if v == "PASSED"],
        "failing": [t for t, v in per_test.items() if v != "PASSED"],
    }
    _BASELINES[tier_id] = baseline
    return baseline


def build_prompt(tier_id: str, tier: dict) -> str:
    parts = ["This repository has a failing test suite.", ""]
    for rel, content in sorted(tier["files"].items()):
        parts += ["--- %s ---" % rel, content]
    baseline = _baseline(tier_id, tier["files"])
    parts += [
        "Running `python -m pytest` reports these failures:",
        *["  " + name for name in baseline["failing"]],
        "",
        "Fix the defect(s) without breaking any test that currently passes. You may "
        "change or add non-test files, including new helper modules. Do not modify "
        "any test file.",
        "Reply with the complete corrected contents of every file you change, one "
        "fenced code block per file, each preceded by a line `### FILE: <relative path>`.",
    ]
    return "\n".join(parts)


def parse_proposals(reply: str, known: dict) -> dict:
    """Map the reply to {relative path: contents}.

    Preferred form is `### FILE: <path>` before each block. A single unlabelled
    block is attributed to the tier's primary file (first non-test module).
    """
    proposals: dict[str, str] = {}
    markers = list(FILE_MARKER.finditer(reply or ""))
    if markers:
        for index, marker in enumerate(markers):
            start = marker.end()
            end = markers[index + 1].start() if index + 1 < len(markers) else len(reply)
            segment = reply[start:end]
            block = CODE_BLOCK.search(segment)
            # Tolerance matters: models often emit the file body after the marker
            # without the requested fence. Rejecting that would score a correct
            # repair as zero, which is a measurement error rather than a model one.
            body = block.group(1) if block else segment
            body = "\n".join(line for line in body.splitlines() if not line.strip().startswith("```"))
            if body.strip():
                proposals[marker.group(1).strip()] = body.strip() + "\n"
        return proposals
    block = CODE_BLOCK.search(reply or "")
    if block:
        primary = next((rel for rel in sorted(known) if not Path(rel).name.startswith("test_")), None)
        if primary:
            proposals[primary] = block.group(1)
    return proposals


class SweLabData(vf.TaskData):
    tier: str = ""
    files: dict[str, str] = {}
    """The tier's initial repository contents."""
    targets: list[str] = []
    """Baseline-failing tests the repair must fix."""
    budgets: dict = {}


class SweLabTask(vf.Task[SweLabData]):
    @vf.stop
    async def single_turn(self, trace: vf.Trace) -> bool:
        return trace.num_turns >= 1

    def _score(self, reply: str):
        baseline = _baseline(self.data.tier, self.data.files)
        proposals = parse_proposals(reply, self.data.files)
        if not proposals:
            return None
        with TemporaryDirectory() as tmp:
            tree = Path(tmp) / "repo"
            for rel, content in self.data.files.items():
                path = tree / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            for rel, content in proposals.items():
                if rel not in self.data.files:
                    continue
                (tree / rel).write_text(content)
            tampered = any(
                Path(rel).name.startswith("test_")
                and proposals.get(rel, self.data.files[rel]) != self.data.files[rel]
                for rel in self.data.files
            )
            return terrain_verifier.verdict_for_tree(tree, baseline, tampered=tampered)

    @vf.reward(weight=1.0)
    async def target_fix_fraction(self, trace: vf.Trace) -> float:
        verdict = self._score(trace.last_reply or "")
        return 0.0 if verdict is None else terrain_verifier.REWARDS["target_fix_fraction"](verdict)

    @vf.reward(weight=0.0)
    async def shaped(self, trace: vf.Trace) -> float:
        verdict = self._score(trace.last_reply or "")
        return 0.0 if verdict is None else terrain_verifier.REWARDS["shaped"](verdict)


class SweLabConfig(vf.TasksetConfig):
    tiers: list[str] = []
    """Restrict the taskset to these tier ids; empty means every tier."""


class SweLabTaskset(vf.Taskset[SweLabTask, SweLabConfig]):
    def load(self) -> list[SweLabTask]:
        tiers = ladder_defs.build_tiers()
        wanted = self.config.tiers or list(tiers)
        tasks = []
        for index, tier_id in enumerate(wanted):
            tier = tiers[tier_id]
            tasks.append(
                SweLabTask(
                    SweLabData(
                        idx=index,
                        name=tier_id,
                        prompt=build_prompt(tier_id, tier),
                        system_prompt=SYSTEM,
                        tier=tier_id,
                        files=dict(tier["files"]),
                        targets=list(tier["targets"]),
                        budgets=dict(tier["budgets"]),
                    ),
                    self.config.task,
                )
            )
        return tasks