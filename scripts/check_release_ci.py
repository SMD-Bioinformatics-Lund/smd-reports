"""Require successful protected-PR checks for the exact tagged release contents."""

import json
import os
import subprocess

QUALITY_JOBS = {"lint", "docs", "core (3.10)", "core (3.12)", "core (3.14)", "pdf"}


def api(path):
    """Read repository metadata through the authenticated GitHub CLI.

    Args:
        path: Repository-relative REST endpoint.

    Returns:
        Decoded GitHub response.
    """
    repository = os.environ["GITHUB_REPOSITORY"]
    return json.loads(
        subprocess.check_output(["gh", "api", f"repos/{repository}/{path}"], text=True)
    )


def tree(commit):
    """Read the Git tree identifier for a local commit.

    Args:
        commit: Commit identifier or HEAD.

    Returns:
        Exact content tree identifier.
    """
    return subprocess.check_output(["git", "rev-parse", f"{commit}^{{tree}}"], text=True).strip()


def verify(release_sha, repository):
    """Require a merged release PR and successful CI on identical contents.

    Args:
        release_sha: Tagged commit on master.
        repository: Expected owner/repository name.

    Raises:
        ValueError: Release ancestry, content identity or successful checks are missing.
    """
    pulls = api(f"commits/{release_sha}/pulls?per_page=100")
    release = next(
        (
            pr
            for pr in pulls
            if pr.get("merged_at")
            and pr.get("merge_commit_sha") == release_sha
            and pr["base"]["ref"] == "master"
            and pr["head"]["ref"] == "dev"
            and pr["head"].get("repo")
            and pr["head"]["repo"]["full_name"] == repository
        ),
        None,
    )
    if release is None:
        raise ValueError("The tag must identify a merged dev-to-master release PR")
    head = release["head"]["sha"]
    if tree(head) != tree(release_sha):
        raise ValueError("Release contents differ from the checked release PR")
    for workflow, required in [("quality.yml", QUALITY_JOBS), ("pr-target.yml", {"branch-flow"})]:
        runs = api(
            f"actions/workflows/{workflow}/runs?head_sha={head}&event=pull_request&status=success&per_page=100"
        )["workflow_runs"]
        valid = False
        for run in runs:
            if (
                run["head_sha"] != head
                or run["head_branch"] != "dev"
                or run["event"] != "pull_request"
                or run["conclusion"] != "success"
                or run["head_repository"]["full_name"] != repository
            ):
                continue
            jobs = api(f"actions/runs/{run['id']}/jobs?per_page=100")["jobs"]
            passed = {job["name"] for job in jobs if job["conclusion"] == "success"}
            if required <= passed:
                valid = True
                break
        if not valid:
            raise ValueError(f"Successful release PR checks are required: {workflow}")


def main():
    """Verify CI before rebuilding distributions for publication."""
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    verify(sha, os.environ["GITHUB_REPOSITORY"])
    print("Release contents match successful protected-PR checks")


if __name__ == "__main__":
    main()
