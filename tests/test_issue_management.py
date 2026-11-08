"""Issue forms, label selection and repository label synchronization."""

import importlib.util
import re
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "manage_issues", ROOT / ".github/scripts/manage_issues.py"
)
management = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(management)


def issue(body, labels=(), state="open"):
    return {"body": body, "state": state, "labels": [{"name": name} for name in labels]}


def test_forms_reference_existing_labels_and_valid_choices():
    definitions = management.label_definitions()
    names = {label["name"] for label in definitions}
    assert len(names) == len(definitions)
    assert all(re.fullmatch("[0-9a-f]{6}", label["color"]) for label in definitions)
    assert all(len(label["description"]) <= 100 for label in definitions)
    forms = list((ROOT / ".github/ISSUE_TEMPLATE").glob("0*.yml"))
    assert len(forms) == 5
    for path in forms:
        form = yaml.safe_load(path.read_text())
        assert set(form["labels"]) <= names
        fields = {field["id"]: field for field in form["body"] if "id" in field}
        assert len(fields) == len([field for field in form["body"] if "id" in field])
        options = fields["priority"]["attributes"]["options"]
        assert set(options) == management.PRIORITIES.keys()
        for heading in ("component", "report-template"):
            for choice in fields[heading]["attributes"]["options"]:
                body_heading = fields[heading]["attributes"]["label"]
                additions, _ = management.label_changes(
                    issue(f"### {body_heading}\n\n{choice}"), {"action": "opened"}
                )
                prefix = "area: " if heading == "component" else "template: "
                selected = {name for name in additions if name.startswith(prefix)}
                assert selected <= names
                assert bool(selected) == (choice not in {"Not sure", "Not template-specific"})


def test_new_issue_labels_include_priority_components_and_template():
    body = (
        "### Priority\n\nP1 - High\n\n### Component\n\nHTML rendering, PDF rendering\n\n"
        "### Report template\n\nCoyote3"
    )
    additions, removals = management.label_changes(issue(body, ["bug"]), {"action": "opened"})
    assert additions == {
        "status: triage",
        "priority: high",
        "area: html",
        "area: pdf",
        "template: coyote3",
    }
    assert not removals


def test_description_edits_preserve_maintainer_labels():
    body = "### Priority\n\nP2 - Normal\n\n### Component\n\nHTML rendering\n\n### Problem\n\n"
    current = issue(
        body + "Updated description",
        ["priority: critical", "status: ready", "area: schema", "help wanted"],
    )
    event = {"action": "edited", "changes": {"body": {"from": body + "Original description"}}}
    assert management.label_changes(current, event) == (set(), set())


def test_component_change_updates_only_its_label_group():
    current = issue(
        "### Component\n\nPDF rendering",
        ["area: html", "priority: high", "status: in progress", "help wanted"],
    )
    event = {"action": "edited", "changes": {"body": {"from": "### Component\n\nHTML rendering"}}}
    assert management.label_changes(current, event) == ({"area: pdf"}, {"area: html"})


def test_priority_change_replaces_previous_priority():
    current = issue("### Priority\n\nP1 - High", ["priority: normal", "status: ready"])
    event = {"action": "edited", "changes": {"body": {"from": "### Priority\n\nP2 - Normal"}}}
    assert management.label_changes(current, event) == ({"priority: high"}, {"priority: normal"})


@pytest.mark.parametrize("state,action", [("closed", "closed"), ("closed", "edited")])
def test_closed_issues_have_no_active_status(state, action):
    current = issue("", ["bug", "status: in progress", "priority: high"], state)
    assert management.label_changes(current, {"action": action}) == (set(), {"status: in progress"})


def test_reopened_issue_returns_to_triage():
    current = issue("", ["bug", "priority: high", "status: in review"])
    assert management.label_changes(current, {"action": "reopened"}) == (
        {"status: triage"},
        {"status: in review"},
    )


def test_unrecognized_form_values_cannot_create_arbitrary_labels():
    current = issue(
        "### Priority\n\nurgent\n\n### Component\n\nnot-a-component\n\n"
        "### Report template\n\nnot-a-template",
        ["bug", "priority: high", "status: ready"],
    )
    assert management.label_changes(current, {"action": "opened"}) == (set(), set())


def test_blank_issue_gets_default_triage_and_priority():
    assert management.label_changes(issue(None), {"action": "opened"}) == (
        {"status: triage", "priority: normal"},
        set(),
    )


def test_breaking_change_request_is_labeled():
    additions, _ = management.label_changes(
        issue("### Breaking change\r\n\r\nYes"), {"action": "opened"}
    )
    assert "breaking change" in additions


def test_label_sync_reads_all_pages_and_preserves_other_labels(monkeypatch):
    desired = {"name": "bug", "color": "d73a4a", "description": "A bug"}
    monkeypatch.setattr(management, "label_definitions", lambda: [desired])
    calls = []

    def api(endpoint, *, method="GET", payload=None):
        calls.append((endpoint, method, payload))
        if endpoint.endswith("&page=1"):
            return [{"name": f"custom-{i}"} for i in range(100)]
        if endpoint.endswith("&page=2"):
            return [{**desired, "description": "Old description"}]

    monkeypatch.setattr(management, "api", api)
    management.sync_labels("owner/repo")
    assert len(calls) == 3
    assert calls[-1] == (
        "repos/owner/repo/labels/bug",
        "PATCH",
        {"color": "d73a4a", "description": "A bug"},
    )


def test_label_sync_does_not_update_unchanged_labels(monkeypatch):
    definitions = management.label_definitions()
    calls = []

    def api(endpoint, *, method="GET", payload=None):
        calls.append(method)
        return definitions

    monkeypatch.setattr(management, "api", api)
    management.sync_labels("owner/repo")
    assert calls == ["GET"]


@pytest.mark.parametrize(
    "selected,previous",
    [("priority: high", "priority: normal"), ("status: ready", "status: triage")],
)
def test_maintainer_label_selection_replaces_previous_value(selected, previous):
    current = issue("", [selected, previous, "bug"])
    assert management.label_changes(
        current, {"action": "labeled", "label": {"name": selected}}
    ) == (set(), {previous})


def test_old_label_event_does_not_restore_a_removed_label():
    current = issue("", ["status: ready"])
    assert management.label_changes(
        current, {"action": "labeled", "label": {"name": "status: triage"}}
    ) == (set(), set())


def test_closed_issue_cannot_receive_active_status():
    current = issue("", ["status: in progress", "priority: high"], state="closed")
    assert management.label_changes(
        current, {"action": "labeled", "label": {"name": "status: in progress"}}
    ) == (set(), {"status: in progress"})
