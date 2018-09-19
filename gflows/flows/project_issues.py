import github
import re

from gflows.workflow import Workflow


class ProjectIssueAutomation(Workflow):
    name = "project_issues"

    def __init__(self, org, project_name, doing_column_id, issue_regex):
        self.org = org
        self.project_name = project_name
        self.doing_column_id = doing_column_id
        self.issue_regex = issue_regex
        self.cards = {}
        self.project_id = None

    def start(self, gh):
        self.project_id = self._id_from_project_name(self.org,
                                                     self.project_name,
                                                     gh)
        self._request_all_cards(gh)

    def _request_all_cards(self, gh):
        project = gh.get_project(self.project_id)
        for column in project.get_columns():
            for card in column.get_cards():
                self._set_card(card.id, card.content_url)

    def hook(self, event_type, data, gh):
        if event_type == "create" and data["ref_type"] == "branch":
            self._handle_branch_update(data, gh)

        if event_type == "project_card":
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
            self.cards = {k: v for k, v in self.cards.items() if v != card_id}

    @staticmethod
    def _id_from_project_name(org, name, gh):
        headers, data = gh._Github__requester.requestJsonAndCheck(
                "GET",
                "/orgs/{}/projects".format(org),
                headers={"Accept": github.Consts.mediaTypeProjectsPreview})

        for p in data:
            if p.get("name") == name:
                return p.get("id")

        raise ValueError("Unknown project name '{}'".format(name))

    def _update_card(self, card_id, gh):
        headers, data = gh._Github__requester.requestJsonAndCheck(
                "GET",
                "/projects/columns/cards/{}".format(card_id),
                headers={"Accept": github.Consts.mediaTypeProjectsPreview}
        )
        content_url = data.get("content_url", "")
        if content_url:
            self._set_card(card_id, content_url)

    def _set_card(self, card_id, content_url):
        if content_url:
            full_repo_name = "/".join(content_url.split("/")[-4:-2])
            issue_number = content_url.split("/")[-1]
            self.cards[full_repo_name + "/" + issue_number] = card_id

    def _move_card(self, card_id, column_id, gh):
        json = {
            "position": "top",
            "column_id": int(column_id)
        }
        headers, data = gh._Github__requester.requestJsonAndCheck(
                "POST",
                "/projects/columns/cards/{}/moves".format(card_id),
                input=json,
                headers={"Accept": github.Consts.mediaTypeProjectsPreview}
        )
        content = data.get("content_url", "")
        if content:
            full_repo_name = "/".join(content.split("/")[-4:-2])
            issue_number = content.split("/")[-1]
            self.cards[full_repo_name + "/" + issue_number] = card_id

    def _handle_branch_update(self, data, gh):

        branch = data["ref"]
        match = re.search(self.issue_regex, branch)
        if match:
            issue_number = match.group(0)
            repository_name = data["repository"]["full_name"]
            card_id = self.cards.get("{}/{}".format(repository_name,
                                                    issue_number))
            if card_id:
                self._move_card(card_id, self.doing_column_id, gh)
