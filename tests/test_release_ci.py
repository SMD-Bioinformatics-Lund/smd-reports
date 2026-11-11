"""Release validation reuse requires trusted successful checks on identical content."""

import importlib.util
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "check_release_ci", ROOT / "scripts/check_release_ci.py"
)
ci = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ci)


@pytest.fixture
def responses(monkeypatch):
    repository = "example/reports"
    pull = {
        "merged_at": "2026-01-01",
        "merge_commit_sha": "release",
        "base": {"ref": "master"},
        "head": {"ref": "dev", "sha": "checked", "repo": {"full_name": repository}},
    }
    runs = {
        name: {
            "id": name,
            "head_sha": "checked",
            "head_branch": "dev",
            "event": "pull_request",
            "conclusion": "success",
            "head_repository": {"full_name": repository},
        }
        for name in ["quality.yml", "pr-target.yml"]
    }
    jobs = {
        "quality.yml": [{"name": name, "conclusion": "success"} for name in ci.QUALITY_JOBS],
        "pr-target.yml": [{"name": "branch-flow", "conclusion": "success"}],
    }

    def api(path):
        if path.startswith("commits/"):
            return [pull]
        if path.startswith("actions/workflows/"):
            name = path.split("/")[2]
            return {"workflow_runs": [runs[name]]}
        name = path.split("/")[2]
        return {"jobs": jobs[name]}

    monkeypatch.setattr(ci, "api", api)
    monkeypatch.setattr(ci, "tree", lambda commit: "same")
    return pull, runs, jobs


def test_identical_release_contents_reuse_successful_checks(responses):
    ci.verify("release", "example/reports")


@pytest.mark.parametrize(
    "failure",
    [
        "fork",
        "wrong-base",
        "unmerged",
        "wrong-commit",
        "changed-tree",
        "failed-run",
        "wrong-event",
        "wrong-branch",
        "wrong-sha",
        "foreign-run",
        "missing-pdf",
        "skipped-pdf",
        "missing-branch-flow",
    ],
)
def test_release_ci_rejects_unverified_or_different_contents(responses, monkeypatch, failure):
    pull, runs, jobs = responses
    if failure == "fork":
        pull["head"]["repo"]["full_name"] = "other/reports"
    if failure == "wrong-base":
        pull["base"]["ref"] = "dev"
    if failure == "unmerged":
        pull["merged_at"] = None
    if failure == "wrong-commit":
        pull["merge_commit_sha"] = "other"
    if failure == "changed-tree":
        monkeypatch.setattr(ci, "tree", lambda commit: commit)
    if failure == "failed-run":
        runs["quality.yml"]["conclusion"] = "failure"
    if failure == "wrong-event":
        runs["quality.yml"]["event"] = "push"
    if failure == "wrong-branch":
        runs["quality.yml"]["head_branch"] = "feature"
    if failure == "wrong-sha":
        runs["quality.yml"]["head_sha"] = "other"
    if failure == "foreign-run":
        runs["quality.yml"]["head_repository"]["full_name"] = "other/reports"
    if failure == "missing-pdf":
        jobs["quality.yml"] = [job for job in jobs["quality.yml"] if job["name"] != "pdf"]
    if failure == "skipped-pdf":
        next(job for job in jobs["quality.yml"] if job["name"] == "pdf")["conclusion"] = "skipped"
    if failure == "missing-branch-flow":
        jobs["pr-target.yml"] = []
    with pytest.raises(ValueError):
        ci.verify("release", "example/reports")


def test_workflows_avoid_duplicate_validation_and_preserve_required_checks():
    quality = yaml.load(
        (ROOT / ".github/workflows/quality.yml").read_text(), Loader=yaml.BaseLoader
    )
    assert quality["on"] == {"pull_request": {"branches": ["dev", "master"]}}
    assert quality["concurrency"]["cancel-in-progress"] == "true"
    assert {"lint", "docs", "core", "pdf"} <= quality["jobs"].keys()
    core = quality["jobs"]["core"]
    assert core["strategy"]["matrix"]["python"] == ["3.10", "3.12", "3.14"]
    for step in core["steps"]:
        if any(
            command in step.get("run", "")
            for command in ["-m build", "twine", "check_installation"]
        ):
            assert step["if"] == "matrix.python == '3.12'"
    release = yaml.load(
        (ROOT / ".github/workflows/release.yml").read_text(), Loader=yaml.BaseLoader
    )
    steps = release["jobs"]["build"]["steps"]
    assert any("check_release_ci.py" in step.get("run", "") for step in steps)
    assert not any("pytest" in step.get("run", "") for step in steps)
    assert any("check_installation.py --source" in step.get("run", "") for step in steps)
    assert release["permissions"]["actions"] == "read"
