import json
import logging
from urllib.parse import urlencode

import os

import requests
from django.http import HttpResponse, JsonResponse
from django.views import View
from django.views.generic import TemplateView
from slackclient import SlackClient

from dialogbot.models import Team, Category
from .mixins import SlackMixin
from .dialogs import category_form


class IndexView(SlackMixin, TemplateView):
    template_name = 'dialogbot/index.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update({
            'title': 'Home',
            'authorization_url': self.get_authorization_url()
        })
        return ctx

    def get_authorization_url(self):
        state = os.urandom(8).hex()
        self.request.session["slack_oauth_state"] = state
        query = urlencode({
            "client_id": self.client_id,
            "scope": self.scopes,
            "redirect_uri": self.get_redirect_url(),
            "state": state
        })

        return "https://slack.com/oauth/authorize?" + query


class OauthCallbackView(SlackMixin, TemplateView):
    template_name = 'dialogbot/auth_result.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        ctx['error'] = kwargs.get('error') or None
        return super().get_context_data(**kwargs)

    def get(self, request, *args, **kwargs):
        response = self.exchange_code_for_token()
        logging.info(response)
        team, created = Team.objects.update_or_create(
            team_id=response["team_id"], app_id=self.client_id, defaults={
                "user_access_token": response["access_token"],
                "bot_access_token": response["bot"]["bot_access_token"],
                "team_name": response['team_name']
            }
        )
        return self.render_to_response(response)

    def exchange_code_for_token(self):
        code = self.request.GET.get("code")
        state = self.request.GET.get("state")
        error = self.request.GET.get("error")

        if error or not state or state != self.request.session.get('slack_oauth_state'):
            return {
                'error': "Error while installing rocket app in your workspace."
            }
        sc = SlackClient("")

        # Request the auth tokens from Slack
        response = sc.api_call(
            "oauth.access",
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.get_redirect_url(),
            code=code
        )

        if not response.get("ok"):
            return {
                'error': "Error while installing rocket app in your workspace."
            }
        return response


class CommandView(SlackMixin, View):
    # for setting team object
    set_team_obj = True

    def post(self, request, *args, **kwargs):
        command = self.data['command'].strip('/')
        try:
            method = getattr(self, f'{command}_command')
        except AttributeError:
            logging.info(f'Unhandled command {command}')
            return HttpResponse(status=200)
        return method()

    def interrupt_command(self):
        resolution_times = [1, 4, 8, 36, 72]
        types = ['Interruption', 'Service Outage']
        categories = Category.objects.values_list('title',flat=True) or ['sample_category']
        sortedCategories = sorted(categories)
        sortedCategories.insert(0, 'None')

        payload = {
            'token': self.team.bot_access_token,
            'trigger_id': self.data['trigger_id'],
            'dialog': json.dumps(category_form(resolution_times, types, sortedCategories))
        }
        response =  requests.post('https://slack.com/api/dialog.open', params=payload)
        return HttpResponse(status=200)


class InteractionView(SlackMixin, View):
    # for setting team object
    set_team_obj = True


    def post(self, request, *args, **kwargs):
        callback_id = self.data['callback_id']
        try:
            method = getattr(self, f'handle_{callback_id}')
        except AttributeError:
            logging.info(f'Unhandled interaction {callback_id}')
            return HttpResponse(status=200)
        return method()

    def handle_category(self):
        print (self.data)
        jiralink = 'https://jira.godaddy.com/browse/{key}'
        submission = self.data['submission']
        username = self.data['user']['name']

        jiraKey = self.createJiraIssue()

        message = {
            'text': "Category Submission Success by `{username}`: ",
            'attachments': get_attachments(submission)
        }

        print (message)
        message1 = {
            'text': "Category Submission Success by `{username}`",
            'text': jiraLink.format(key=jiraKey)
        }
        requests.post(self.data['response_url'], data=json.dumps(message))

        return HttpResponse(status=200)

    def createJiraIssue(self):
        activeSprint = 'https://jira.godaddy.com/rest/agile/1.0/board/373/sprint?state=active'
        jsonStr = '{"fields": {"customfield_10007" : 19474, "project": {"key": "PKI"},"summary": "Test","issuetype": {"id": 8},"labels": ["Interruption","PKIDev"],"description": "This is an interruption. Auto-generated by PKIBot", "reporter" : {"name" : "mmurray"}, "assignee" : {"name" : "mmurray"}}}'

        transitionurl = 'https://jira.godaddy.com/rest/api/2/issue/{key}/transitions?expand=transitions.fields'

        #transition to done
        transitionStr = '{"transition": {"id": "251"}}'
        createjira = 'https://jira.godaddy.com/rest/api/2/issue'
        submission = self.data['submission']
        username = self.data['user']['name']

        currentSprint = self.getResults(activeSprint)
        labels = ['Interruption']
        labels = self.retrieveCategoryLabels(labels)
        labels = self.retrieveTeamLabels(labels, username)

        desc = submission['description']
        x = {
            "fields":
            {
                "customfield_10004" : self.populateStoryPoints(),
                "customfield_10007" : currentSprint['values'][0]['id'],
                "project": {"key": "PKI"},
                "summary": "Interruption: " + submission['summary'],
                "issuetype": {"id": 8},
                "labels": labels,
                "description": desc,
                "reporter" : {"name" : username},
                "assignee" : {"name" : username}
            }
        }

        print (x)
        #ll = json.loads(jsonStr)

        response = self.postResponse(createjira, x)
        print (response.content, response.status_code)

        if response.status_code == 201:
            rr = json.loads(response.content)
            print (rr)

            self.postResponse(transitionurl.format(key=rr['key']), transitionStr)

        return rr['key']

    def populateStoryPoints(self):
        time = int(self.data['submission']['resolution_time'])
        if time == 1:
            return 1

        if time == 4:
            return 2

        if time == 8:
            return 3

        if time == 36:
            return 5

        if time == 72:
            return 8

        return 1

    def retrieveCategoryLabels(self, labels):
        submission = self.data['submission']
        if submission['category_1'] != 'None':
            labels.append(submission['category_1'])

        #if submission['category_2'] != 'None':
        #    labels.append(submission['category_2'])

        return labels

    def retrieveTeamLabels(self, labels, username):
        pki_ops = ['jstack', 'jdarr', 'dwilliams1', 'jdhurano', 'ddubovik']
        team_snafu = ['astokes', 'mxpatterson', 'rjasmin']
        team_skittlebräu = ['ahough', 'ppettong', 'jgorz', 'schang']
        team_fu = ['rmartin', 'adharamsey', 'asink', 'mmurray']

        if username in pki_ops:
            labels.append('PKIOps')
            return labels

        if username in team_snafu:
            labels.append('TeamSnafu')

        if username in team_skittlebräu:
            labels.append('TeamSkittlebräu')

        if username in team_fu:
            labels.append('TeamFU')

        labels.append('PKIDev')

        return labels

    def getResults(self, url):
        headers = {"Accept": "application/json", "Content-Type": "application/json",
                   "Authorization": "Basic MDJkODQ4NnJ5NWhBOlduNDEjWSViNW18X3Ez"}
        r = requests.get(url, headers=headers);

        return json.loads(r.content)

    def postResponse(self, url, body):
        headers = {"Accept": "application/json", "Content-Type": "application/json",
                   "Authorization": "Basic MDJkODQ4NnJ5NWhBOlduNDEjWSViNW18X3Ez"}
        print (body)
        r = requests.post(url, headers=headers, data=body);
        print (r)
        return r


def get_attachments(submission):
    fields = [
        {
            "title": key.replace("_", " ").title(),
            "value": value
        }
        for key, value in submission.items()
    ]
    attachment = {
        "color": "#aaefab",
        "mrkdwn_in": ['fields', 'text', 'pretext'],
        "fields": fields,
        'footer': 'Category',
    }
    return [attachment]
