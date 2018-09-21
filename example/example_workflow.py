import os

import logging

from gflows import Workflows
from gflows.flows import (
    ShareLabelsAccrossRepositories, CloseIssuesInColumn,
    MoveIssues)

config = {
    "gh_token": os.environ.get("GITHUB_TOKEN"),
}

if __name__ == '__main__':
    """Contains test workflows used for gflow."""

    logging.basicConfig(level="DEBUG")

    workflows = Workflows(
            login_or_token=config["gh_token"])

    workflows.add(ShareLabelsAccrossRepositories(
            repositories=["tmbo/gflows", "tmbo/test"]))

    workflows.add(MoveIssues(org="MyOrganization",
                             project_name="Sprint Board",
                             origin_column=2532176,
                             target_column=2623467))

    workflows.add(CloseIssuesInColumn(org="RasaHQ",
                                      project_name="Sprint Board",
                                      column=3045619))

    workflows.run()
