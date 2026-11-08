"""Synchronize repository labels and label issues submitted through GitHub forms."""

import argparse
import json
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[2]
PRIORITIES = {
    "P0 - Critical": "priority: critical",
    "P1 - High": "priority: high",
    "P2 - Normal": "priority: normal",
    "P3 - Low": "priority: low",
}


def label_definitions():
    """Read label names, colors and descriptions from the repository configuration."""
    return json.loads((ROOT / ".github/labels.json").read_text(encoding="utf-8"))


def form_field(body, heading):
    """Read one field from the Markdown produced by a GitHub issue form.

    Args:
        body: Issue body text.
        heading: Exact field heading used by the form.

    Returns:
        The field text, or None when the heading is absent.
    """
    match = re.search(
        rf"^### {re.escape(heading)}\s*\n(.*?)(?=^### |\Z)",
        (body or "").replace("\r\n", "\n"),
        re.M | re.S,
    )
    return match[1].strip() if match else None


def label_changes(issue, event):
    """Determine label changes without overwriting unrelated maintainer edits.

    Args:
        issue: Current issue returned by GitHub, including its labels and state.
        event: GitHub issue event, including the previous body when edited.

    Returns:
        Sets of label names to add and remove.
    """
    current = {label["name"] for label in issue["labels"]}
    desired = current.copy()
    body = issue.get("body") or ""
    previous = event.get("changes", {}).get("body", {}).get("from", body)
    action = event["action"]
    if action == "labeled":
        selected = event.get("label", {}).get("name", "")
        configured = {label["name"] for label in label_definitions()}
        if selected in current and selected in configured:
            for prefix in ("priority: ", "status: "):
                if selected.startswith(prefix):
                    desired -= {name for name in desired if name.startswith(prefix)}
                    desired.add(selected)
        if issue["state"] == "closed":
            desired -= {name for name in desired if name.startswith("status: ")}
        return desired - current, current - desired
    if issue["state"] == "closed":
        desired -= {name for name in desired if name.startswith("status: ")}
        return desired - current, current - desired
    statuses = {name for name in desired if name.startswith("status: ")}
    if action == "reopened" or not statuses:
        desired -= statuses
        desired.add("status: triage")
    priority = form_field(body, "Priority")
    if not any(name.startswith("priority: ") for name in current) or (
        priority in PRIORITIES and priority != form_field(previous, "Priority")
    ):
        desired -= {name for name in desired if name.startswith("priority: ")}
        desired.add(PRIORITIES.get(priority, "priority: normal"))
    definitions = label_definitions()
    mappings = {
        "Component": {
            label["description"]: label["name"]
            for label in definitions
            if label["name"].startswith("area: ")
        },
        "Report template": {
            label["description"].removesuffix(" report template"): label["name"]
            for label in definitions
            if label["name"].startswith("template: ")
        },
    }
    for heading, choices in mappings.items():
        value = form_field(body, heading)
        if value is None or (action != "opened" and value == form_field(previous, heading)):
            continue
        selected = {item.strip() for item in value.split(",")}
        if selected <= choices.keys() | {"Not sure", "Not template-specific"}:
            prefix = "area: " if heading == "Component" else "template: "
            desired -= {name for name in desired if name.startswith(prefix)}
            desired |= {choices[item] for item in selected if item in choices}
    if form_field(body, "Breaking change") == "Yes" and (
        action == "opened" or form_field(previous, "Breaking change") != "Yes"
    ):
        desired.add("breaking change")
    return desired - current, current - desired


def api(endpoint, *, method="GET", payload=None):
    """Call GitHub using the credentials already configured for the GitHub CLI.

    Args:
        endpoint: Repository API path.
        method: HTTP method.
        payload: Optional JSON request body.

    Returns:
        The decoded response, or None for an empty response.

    Raises:
        subprocess.CalledProcessError: GitHub rejects the request.
    """
    command = ["gh", "api", "--method", method, endpoint]
    if payload is not None:
        command += ["--input", "-"]
    output = subprocess.check_output(
        command, input=json.dumps(payload) if payload is not None else None, text=True
    )
    return json.loads(output) if output.strip() else None


def sync_labels(repository):
    """Create or update configured labels without deleting other repository labels.

    Args:
        repository: GitHub owner/repository name.
    """
    existing = {}
    page = 1
    while True:
        labels = api(f"repos/{repository}/labels?per_page=100&page={page}")
        existing.update({label["name"]: label for label in labels})
        if len(labels) < 100:
            break
        page += 1
    for label in label_definitions():
        current = existing.get(label["name"])
        if current is None:
            api(f"repos/{repository}/labels", method="POST", payload=label)
        elif any(current.get(key) != value for key, value in label.items()):
            api(
                f"repos/{repository}/labels/{quote(label['name'], safe='')}",
                method="PATCH",
                payload={"color": label["color"], "description": label["description"]},
            )
    print(f"Synchronized {len(label_definitions())} issue labels")


def main(argv=None):
    """Run label synchronization or process the current GitHub issue event.

    Args:
        argv: Command arguments. None reads sys.argv.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["sync-labels", "label-issue"])
    args = parser.parse_args(argv)
    repository = os.environ["GITHUB_REPOSITORY"]
    if args.command == "sync-labels":
        sync_labels(repository)
        return
    event = json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))
    endpoint = f"repos/{repository}/issues/{int(event['issue']['number'])}"
    issue = api(endpoint)
    additions, removals = label_changes(issue, event)
    for name in sorted(removals):
        api(f"{endpoint}/labels/{quote(name, safe='')}", method="DELETE")
    if additions:
        api(f"{endpoint}/labels", method="POST", payload={"labels": sorted(additions)})
    print(f"Updated issue #{issue['number']}: {len(additions)} added, {len(removals)} removed")


if __name__ == "__main__":
    main()
