import logging
from github import UnknownObjectException, GithubException
from github.GithubObject import NotSet
from github.Label import Label

from gflows.workflow import Workflow

logger = logging.getLogger(__name__)


class ShareLabelsAccrossRepositories(Workflow):
    name = "shared_labels"

    def __init__(self, repositories):
        """Creates the same label on all repositories."""
        self.repositories = [r.lower() for r in repositories]

    @staticmethod
    def _update_or_create_label(repo, name, label):
        try:
            l: Label = repo.get_label(name)
            if (l.color != label["color"]
                    or l.name != label["name"]
                    or l.description != label.get("description")):

                l.edit(label["name"],
                       label["color"],
                       label.get("description", NotSet))
                logger.info("Updated Label {} on repo {}.".format(
                        l.name, repo.full_name))
        except UnknownObjectException:
            repo.create_label(
                    label["name"],
                    label["color"],
                    label.get("description", NotSet))
            logger.info("Created Label {} on repo {}.".format(
                    label["name"], repo.full_name))

    @staticmethod
    def _delete_label(repo, name):
        try:
            l: Label = repo.get_label(name)
            l.delete()
            logger.info("Removed Label {} from repo {}.".format(
                    l.name, repo.full_name))
        except UnknownObjectException:
            pass

    def hook(self, event_type, data, gh):
        if (event_type != "label" or
                data["repository"][
                    "full_name"].lower() not in self.repositories):
            return

        repositories = [r
                        for r in self.repositories
                        if r != data["repository"]["full_name"].lower()]

        action = data.get("action")
        if action == "created":
            for repository in repositories:
                try:
                    repo = gh.get_repo(repository)
                    self._update_or_create_label(
                            repo,
                            data["label"]["name"],
                            data["label"])
                except UnknownObjectException:
                    continue
                except GithubException:
                    continue
        elif action == "edited":
            for repository in repositories:
                try:
                    repo = gh.get_repo(repository)
                    name = (data["changes"].get("name", {}).get("from") or
                            data["label"]["name"])
                    self._update_or_create_label(
                            repo,
                            name,
                            data["label"])
                except UnknownObjectException:
                    continue
                except GithubException:
                    continue
        elif action == "deleted":
            for repository in repositories:
                try:
                    repo = gh.get_repo(repository)
                    self._delete_label(repo, data["label"]["name"])
                except UnknownObjectException:
                    continue
                except GithubException:
                    continue
