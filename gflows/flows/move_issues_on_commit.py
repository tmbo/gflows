import logging
import re
from github import Github, UnknownObjectException
from github.GithubObject import NotSet
from github.Issue import Issue
from github.Repository import Repository
from typing import Text

from gflows.flows import utils
from gflows.workflow import Workflow

logger = logging.getLogger(__name__)


class MoveIssues(Workflow):
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

    @staticmethod
    def _extract_move_target(text: Text):
        match = re.search("/move\s+(to)?\s*([^\s]+)", text)
        if match:
            return match.group(2)
        else:
            return None

    @staticmethod
    def _has_permissions(gh: Github, user: Text, source_repo: Text,
                         target_repo: Text):
        return (utils.has_write_permissions(user, source_repo, gh) and
                utils.has_write_permissions(user, target_repo, gh))

    def hook(self, event_type, data, gh):
        if event_type == "push":
            self._handle_commit(data, gh)

        elif event_type == "project_card":
            self._handle_card_update(data, gh)

        elif event_type == "issue_comment":
            self._handle_move_command(data, gh)

    def _handle_move_command(self, data, gh):
        target_repo = self._extract_move_target(data["comment"]["body"])
        if not target_repo:
            return
        try:
            source_repo = data["repository"]["full_name"]

            if "/" not in target_repo:
                target_repo = source_repo.split("/")[0] + "/" + target_repo

            if self._has_permissions(gh,
                                     data["sender"]["login"],
                                     data["repository"]["full_name"],
                                     target_repo):
                if source_repo.lower() != target_repo.lower():
                    self._move_issue(data["issue"]["number"],
                                     source_repo,
                                     target_repo,
                                     gh)
                else:
                    self._comment_same_repo(data["issue"]["number"],
                                            source_repo,
                                            gh)
        except UnknownObjectException:
            self._comment_invalid_target(data["issue"]["number"],
                                         data["repository"]["full_name"],
                                         target_repo,
                                         gh)

    def _comment_invalid_target(self, issue_number, source_name, target_repo,
                                gh):
        source: Repository = gh.get_repo(source_name)

        issue = source.get_issue(issue_number)
        issue.create_comment("Can't move, I don't know the repo '{}' 😅"
                             "".format(target_repo))

    def _comment_same_repo(self, issue_number, source_name, gh):
        source: Repository = gh.get_repo(source_name)

        issue = source.get_issue(issue_number)
        issue.create_comment("Can't move, issue is already on this repo. 😅")

    def _move_issue(self, issue_number, source_name, target_name, gh):
        logger.info("Moved Issue #{} from '{}' to '{}'.".format(
                issue_number,
                source_name,
                target_name))

        target: Repository = gh.get_repo(target_name)
        source: Repository = gh.get_repo(source_name)

        issue = source.get_issue(issue_number)

        if target.private or not source.private:
            body = issue.body + "\n\n Moved from {}".format(issue.html_url)
        else:
            body = issue.body

        valid_labels = {l.name for l in target.get_labels()}
        issue_labels = [l.name for l in issue.labels if l.name in valid_labels]
        moved_issue: Issue = target.create_issue(
                issue.title,
                body or NotSet,
                labels=issue_labels or NotSet,
                assignees=issue.assignees or NotSet)

        for c in issue.get_comments():
            if not self._extract_move_target(c.body):
                comment = "[{}]({}) commented on _{}_:\n\n{}".format(
                        c.user.login, c.user.html_url, c.created_at, c.body)
                moved_issue.create_comment(comment)

        if source.private or not target.private:
            issue.create_comment("Moved to {}".format(moved_issue.html_url))

        issue.edit(state="closed")

        card_id, column_id = self.cards.get(
                "{}/{}".format(source_name, issue_number), (None, None))

        if card_id and column_id:
            utils.create_card_on_column(moved_issue.id, column_id, gh)
            utils.remove_card(card_id, gh)

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
