import json

import requests
from django_rq import job

from dialogbot.attachments import get_attachments
from dialogbot.utils.jira import JiraHandler


@job
def handle_jira(data):
    submission = data['submission']
    username = data['user']['name']

    jira_handler = JiraHandler(data)
    jira_key = jira_handler.createJiraIssue()
    jira_link = f"https://jira.godaddy.com/browse/{jira_key}"
    message = {
        'text': f"Jira Link: {jira_link}",
        'attachments': get_attachments(submission)
    }
    requests.post(data['response_url'], data=json.dumps(message))
