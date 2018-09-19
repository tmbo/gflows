import hashlib
import hmac
import logging

from flask import Flask, request, abort


logger = logging.getLogger(__name__)


def _get_digest(secret=None):
    """Return message digest if a secret key was provided"""

    if secret:
        return hmac.new(secret, request.data, hashlib.sha1).hexdigest()
    else:
        return None


def _get_header(key):
    """Return message header"""

    try:
        return request.headers[key]
    except KeyError:
        abort(400, 'Missing header: ' + key)


def create_app(hook, gh_secret=None):
    app = Flask(__name__)

    @app.route("/health")
    def hello_world():
        return "all save and sound"

    @app.route("/postreceive", methods=["POST"])
    def on_push():
        """Callback from Flask"""

        digest = _get_digest(gh_secret)

        if digest is not None:
            sig_parts = _get_header('X-Hub-Signature').split('=', 1)

            if (len(sig_parts) < 2 or sig_parts[0] != 'sha1'
                    or not hmac.compare_digest(sig_parts[1], digest)):
                abort(400, 'Invalid signature')

        event_type = _get_header('X-Github-Event')
        data = request.get_json()

        if data is None:
            abort(400, 'Request body must contain json')

        logger.info(
                '%s (%s)', _format_event(event_type, data),
                _get_header('X-Github-Delivery'))

        hook(event_type, data)

        return '', 204

    return app


EVENT_DESCRIPTIONS = {
    'commit_comment': '{comment[user][login]} commented on '
                      '{comment[commit_id]} in {repository[full_name]}',
    'create': '{sender[login]} created {ref_type} ({ref}) in '
              '{repository[full_name]}',
    'delete': '{sender[login]} deleted {ref_type} ({ref}) in '
              '{repository[full_name]}',
    'deployment': '{sender[login]} deployed {deployment[ref]} to '
                  '{deployment[environment]} in {repository[full_name]}',
    'deployment_status': 'deployment of {deployement[ref]} to '
                         '{deployment[environment]} '
                         '{deployment_status[state]} in '
                         '{repository[full_name]}',
    'fork': '{forkee[owner][login]} forked {forkee[name]}',
    'gollum': '{sender[login]} edited wiki pages in {repository[full_name]}',
    'issue_comment': '{sender[login]} commented on issue #{issue[number]} '
                     'in {repository[full_name]}',
    'issues': '{sender[login]} {action} issue #{issue[number]} in '
              '{repository[full_name]}',
    'member': '{sender[login]} {action} member {member[login]} in '
              '{repository[full_name]}',
    'membership': '{sender[login]} {action} member {member[login]} to team '
                  '{team[name]} in {repository[full_name]}',
    'page_build': '{sender[login]} built pages in {repository[full_name]}',
    'ping': 'ping from {sender[login]}',
    'public': '{sender[login]} publicized {repository[full_name]}',
    'pull_request': '{sender[login]} {action} pull #{pull_request[number]} in '
                    '{repository[full_name]}',
    'pull_request_review': '{sender[login]} {action} {review[state]} review '
                           'on pull #{pull_request[number]} in '
                           '{repository[full_name]}',
    'pull_request_review_comment': '{comment[user][login]} {action} comment '
                                   'on pull #{pull_request[number]} in '
                                   '{repository[full_name]}',
    'push': '{pusher[name]} pushed {ref} in {repository[full_name]}',
    'release': '{release[author][login]} {action} {release[tag_name]} in '
               '{repository[full_name]}',
    'repository': '{sender[login]} {action} repository '
                  '{repository[full_name]}',
    'status': '{sender[login]} set {sha} status to {state} in '
              '{repository[full_name]}',
    'team_add': '{sender[login]} added repository {repository[full_name]} to '
                'team {team[name]}',
    'watch': '{sender[login]} {action} watch in repository '
             '{repository[full_name]}'
}


def _format_event(event_type, data):
    try:
        return EVENT_DESCRIPTIONS[event_type].format(**data)
    except KeyError:
        return event_type


if __name__ == "__main__":
    logging.basicConfig(level="DEBUG")
    create_app().run(host="0.0.0.0", port=8383)
