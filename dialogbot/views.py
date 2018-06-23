from urllib.parse import urlencode

import os
from django.views.generic import TemplateView
from slackclient import SlackClient

from dialogbot.mixins import SlackMixin


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