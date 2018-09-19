import logging
from github import Github
from typing import Text

from gflows.flows import utils
from gflows.workflow import Workflow

logger = logging.getLogger(__name__)


class CloseIssuesInColumn(Workflow):
    """Makes sure that issues that get moved to a certain column get closed.

    Listens to events for a certain project and its done column. If
    an issue is moved to that column, it will automatically get closed."""

    name = "close_issues_in_column"

    def __init__(self, org, project_name, column):
        self.org = org
        self.project_name = project_name
        self.column_id = column
        self.project_id = None

    def start(self, gh: Github):
        self.project_id = utils.id_from_project_name(
                self.org, self.project_name, gh)

    def hook(self, event_type, data, gh):
        if event_type == "project_card":
            self._handle_card_update(data, gh)

    def _handle_card_update(self, data, gh):
        project_id = int(data["project_card"]["project_url"].split("/")[-1])
        if not project_id == self.project_id:
            return

        if (data["action"] == "moved"
                and data["project_card"]["column_id"] == self.column_id):

            card_id = data["project_card"]["id"]
            self._close_issue_of_card(card_id, gh)

    @staticmethod
    def _close_issue_of_card(card_id: Text, gh):
        issue = utils.issue_from_card_id(card_id, gh)
        if issue:
            issue.edit(state="closed")
            logger.info("Closed issue {}".format(issue.url))
