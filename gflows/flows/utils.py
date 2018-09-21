import re
from github import Consts, Github
from github.Issue import Issue
from typing import Text, Optional, Any, Dict


def id_from_project_name(org: Text, name: Text, gh: Github) -> Text:
    """Return the id of a project on an organization."""

    headers, data = gh_request(
            gh,
            "GET",
            "/orgs/{}/projects".format(org),
            headers={"Accept": Consts.mediaTypeProjectsPreview})

    for p in data:
        if p.get("name") == name:
            return p.get("id")

    raise ValueError("Unknown project name '{}'".format(name))


def issue_from_card_id(card_id: Text, gh: Github) -> Optional[Issue]:
    """Fetch the github issue from a card id."""

    headers, data = gh_request(
            gh,
            "GET",
            "/projects/columns/cards/{}".format(card_id),
            headers={"Accept": Consts.mediaTypeProjectsPreview}
    )
    content_url = data.get("content_url", "")
    if content_url:
        full_repo_name = "/".join(content_url.split("/")[-4:-2])
        issue_number = int(content_url.split("/")[-1])
        repo = gh.get_repo(full_repo_name)
        return repo.get_issue(issue_number)
    else:
        return None


def get_card_json(card_id: Text, gh: Github) -> Dict[Text, Any]:
    """Return the dict representation of a card."""

    _, data = gh_request(
            gh,
            "GET",
            "/projects/columns/cards/{}".format(card_id),
            headers={"Accept": Consts.mediaTypeProjectsPreview}
    )
    return data


def move_card_to_column(card_id: Text,
                        target_column_id: int,
                        gh: Github) -> None:
    """Move a card on a project board to a column."""

    json = {
        "position": "top",
        "column_id": target_column_id
    }

    gh_request(
            gh,
            "POST",
            "/projects/columns/cards/{}/moves".format(card_id),
            input=json,
            headers={"Accept": Consts.mediaTypeProjectsPreview}
    )


def create_card_on_column(issue_id: Text,
                          column_id: Text,
                          gh: Github) -> None:
    """Move a card on a project board to a column."""

    json = {
        "content_type": "Issue",
        "content_id": issue_id
    }

    gh_request(
            gh,
            "POST",
            "/projects/columns/{}/cards".format(column_id),
            input=json,
            headers={"Accept": Consts.mediaTypeProjectsPreview}
    )


def remove_card(card_id: Text, gh: Github) -> None:
    """Move a card on a project board to a column."""

    gh_request(
            gh,
            "DELETE",
            "/projects/columns/cards/{}".format(card_id),
            headers={"Accept": Consts.mediaTypeProjectsPreview}
    )


def has_write_permissions(user: Text, repo: Text, gh: Github):
    p = gh.get_repo(repo).get_collaborator_permission(user)
    return p in ["admin", "write"]


def issue_id_from_commit_message(commit_message: Text) -> Optional[int]:
    """Return the issue referenced in a commit message.

    If there is no issue reference, `None` is returned."""

    match = re.search("#(\d+)", commit_message)
    if match:
        return int(match.group(1))
    else:
        return None


def gh_request(gh: Github, *args: Any, **kwargs: Any):
    """Send a request to the github endpoint."""

    # unfortunately, the library doesn't expose this yet, so we need to
    # do a hacky workaround
    # noinspection PyProtectedMember,PyUnresolvedReferences
    return gh._Github__requester.requestJsonAndCheck(
            *args,
            **kwargs
    )
