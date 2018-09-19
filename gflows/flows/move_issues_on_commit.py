import logging
from github import Github

from gflows.flows import utils
from gflows.workflow import Workflow

logger = logging.getLogger(__name__)


class MoveIssuesOnCommit(Workflow):
    """Automatically moves issues on a project board when there is a commit.

    If a commit to the issue is made, and the issue has been in the
    origin column, it will be moved to the target column."""

    name = "project_issues"

    def __init__(self, org, project_name, origin_column, target_column):
        self.org = org
        self.project_name = project_name
        self.origin_column = origin_column
        self.target_column = target_column
        self.cards = {}
        self.project_id = None

    def start(self, gh: Github):
        self.project_id = utils.id_from_project_name(
                self.org, self.project_name, gh)
        self._request_all_cards(gh)

    def _request_all_cards(self, gh):
        project = gh.get_project(self.project_id)
        for column in project.get_columns():
            for card in column.get_cards():
                column_id = int(card.column_url.split("/")[-1])
                self._set_card(card.id, card.content_url, column_id)

    def hook(self, event_type, data, gh):
        if event_type == "push":
            self._handle_commit(data, gh)

        elif event_type == "project_card":
            self._handle_card_update(data, gh)

    def _handle_card_update(self, data, gh):
        project_id = int(data["project_card"]["project_url"].split("/")[-1])
        if not project_id == self.project_id:
            return

        if data["action"] == "created":
            card_id = data["project_card"]["id"]
            self._update_card(card_id, gh)
        elif data["action"] == "converted":
            card_id = data["project_card"]["id"]
            self._update_card(card_id, gh)
        elif data["action"] == "deleted":
            card_id = data["project_card"]["id"]
            self.cards = {k: v
                          for k, v in self.cards.items()
                          if v != card_id}

    def _update_card(self, card_id, gh):
        data = utils.get_card_json(card_id, gh)
        content_url = data.get("content_url", "")
        if content_url:
            column_id = int(data["column_url"].split("/")[-1])
            self._set_card(card_id, content_url, column_id)

    def _set_card(self, card_id, content_url, column_id):
        if content_url:
            full_repo_name = "/".join(content_url.split("/")[-4:-2])
            issue_number = content_url.split("/")[-1]
            self.cards[full_repo_name + "/" + issue_number] = card_id, column_id

    def _move_card(self, card_id, column_id, gh):
        utils.move_card_to_column(card_id, column_id, gh)

        data = utils.get_card_json(card_id, gh)
        logger.info("Moved Card {} to column {} in project '{}'.".format(
                data.get("url"),
                data.get("column_url"),
                self.project_name))

        content_url = data.get("content_url", "")
        if content_url:
            column_id = int(data["column_url"].split("/")[-1])
            self._set_card(card_id, content_url, column_id)

    def _handle_commit(self, data, gh):
        for c in data["commits"]:
            if not c["distinct"]:
                continue

            issue_number = utils.issue_id_from_commit_message(c["message"])
            if not issue_number:
                continue

            repository_name = data["repository"]["full_name"]
            card_id, column_id = self.cards.get(
                    "{}/{}".format(repository_name, issue_number), (None, None))

            if card_id and column_id == self.origin_column:
                self._move_card(card_id, self.target_column, gh)
