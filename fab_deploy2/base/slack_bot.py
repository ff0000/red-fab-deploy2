import json
import requests

from django.conf import settings


def slack_post_msg(team_id, channel_id, token, channel, project_name, server,
                   bot_name="deploy-bot", bot_emoji="monkey"):
    """
    Generic function for posting messages to Slack channel
    """
    slack_url = "https://hooks.slack.com/services/{0}/{1}/{2}".format(team_id,
                                                                      channel_id,
                                                                      token)
    msg = "{0} code has been pushed to {1}".format(project_name, server)
    payload = {
        "text": msg,
        "channel": "#{0}".format(channel),
        "username": bot_name,
        "icon_emoji": ":{0}:".format(bot_emoji),
    }
    requests.post(slack_url, data=json.dumps(payload))


def slack_put_msg(server):
    """
    POSTing deployment message to slack channel reading params from `settings.py`

    This function should be called from `fab.deploy` task
    """
    # Checking if required params were configured on `settings.py`
    if settings.get("SLACK_TEAM_ID") and settings.get("SLACK_CHANNEL_ID") and \
            settings.get("SLACK_TOKEN") and settings.get("SLACK_CHANNEL") and \
            settings.get("SLACK_PROJECT_NAME"):
        slack_post_msg(settings.get("SLACK_TEAM_ID"), settings.get("SLACK_CHANNEL_ID"),
                       settings.get("SLACK_TOKEN"), settings.get("SLACK_CHANNEL"),
                       settings.get("SLACK_PROJECT_NAME"), server)
