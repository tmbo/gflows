from github import UnknownObjectException, Label
from github.GithubObject import NotSet

from gflows.workflow import Workflow


class SharedLabels(Workflow):
    name = "shared_labels"

    def __init__(self, repositories):
        """Creates the same label on all repositories."""
        self.repositories = [r.lower() for r in repositories]

    @staticmethod
    def _update_or_create_label(repo, name, label):
        try:
            l: Label = repo.get_label(name)
            l.edit(label["name"],
                   label["color"],
                   label.get("description", NotSet))
        except UnknownObjectException:
            repo.create_label(
                    label["name"],
                    label["color"],
                    label.get("description", NotSet))

    @staticmethod
    def _delete_label(repo, name):
        try:
            l: Label = repo.get_label(name)
            l.delete()
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
        elif action == "deleted":
            for repository in repositories:
                try:
                    repo = gh.get_repo(repository)
                    self._delete_label(repo, data["label"]["name"])
                except UnknownObjectException:
                    continue
