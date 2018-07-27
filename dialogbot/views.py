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
        resolution_times = [1, 4, 8, 12]
        types = ['Interruption', 'Service Outage']
        categories = Category.objects.values_list('title',flat=True) or ['sample_category']
        payload = {
            'token': self.team.bot_access_token,
            'trigger_id': self.data['trigger_id'],
            'dialog': json.dumps(category_form(resolution_times, types, categories))
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
        submission = self.data['submission']
        username = self.data['user']['name']
        message = {
            'text': f"Category Submission Success by `{username}`",
            'attachments': get_attachments(submission)
        }
        requests.post(self.data['response_url'], data=json.dumps(message))
        return HttpResponse(status=200)


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
