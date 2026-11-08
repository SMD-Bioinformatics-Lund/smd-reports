"""Release checks reject feature-only tags without touching the working repository."""

import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "check_release", Path(__file__).parents[1] / "scripts/check_release.py"
)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


@pytest.mark.skipif(shutil.which("git") is None, reason="Git is required for ancestry checks")
def test_release_must_be_tagged_on_master(tmp_path, monkeypatch):
    def git(*args):
        return subprocess.check_output(
            ["git", *args], cwd=tmp_path, text=True, stderr=subprocess.DEVNULL
        ).strip()

    package = tmp_path / "src/smd_reports"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text('__version__ = "0.1.0"\n')
    git("init", "--initial-branch=master")
    git("config", "user.name", "Synthetic release test")
    git("config", "user.email", "release-test@example.org")
    git("add", "src")
    git("commit", "-m", "Synthetic master")
    master = git("rev-parse", "HEAD")
    git("update-ref", "refs/remotes/origin/master", master)
    git("checkout", "-b", "feature")
    (tmp_path / "feature.txt").write_text("Synthetic feature\n")
    git("add", "feature.txt")
    git("commit", "-m", "Synthetic feature")
    git("tag", "v0.1.0")
    monkeypatch.setattr(release, "ROOT", tmp_path)
    with pytest.raises(subprocess.CalledProcessError):
        release.check("v0.1.0", check_git=True)
    git("tag", "-d", "v0.1.0")
    git("checkout", "master")
    git("tag", "v0.1.0")
    assert release.check("v0.1.0", check_git=True) == "0.1.0"
    with pytest.raises(ValueError, match="package version"):
        release.check("v9.9.9")
