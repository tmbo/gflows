import logging
from github import Github
from typing import List, Dict, Text, Any

from gflows.server import create_app

logger = logging.getLogger(__name__)


class Workflow:
    def start(self, gh: Github):
        pass

    def hook(self, event_type: str, data: Dict[Text, Any], gh: Github):
        pass


class Workflows:

    def __init__(self, login_or_token=None, password=None, secret=None,
                 **kwargs):
        self.gh = Github(login_or_token, password, **kwargs)
        self.secret = secret
        self.workflows: List[Workflow] = []

    def add(self, workflow):
        self.workflows.append(workflow)

    def hook(self, event_type, payload):
        for workflow in self.workflows:
            try:
                workflow.hook(event_type, payload, self.gh)
            except Exception as e:
                logger.exception("Hook failed. Payload: {}".format(payload))

    def app(self):
        for workflow in self.workflows:
            workflow.start(self.gh)

        return create_app(self.hook, self.secret)

    def run(self, port=8383):
        self.app().run(host="0.0.0.0", port=port)
