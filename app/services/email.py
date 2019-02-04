import requests
from flask import url_for, render_template

from config import MAILGUN_URL, MAILGUN_API_KEY, DEFAULT_EMAIL_FROM_ADDRESS


def send_confirmation_email(email_address, token):
    requests.post(
        url=f"https://api.mailgun.net/v2/{MAILGUN_URL}/messages",
        auth=('api', MAILGUN_API_KEY),
        data={
            'from': DEFAULT_EMAIL_FROM_ADDRESS,
            'to': email_address,
            'subject': 'Alpha-I Detection Service | Please confirm your email address',
            'text': url_for('user.confirm', token=token, _external=True),
            'html': render_template(
                'email/confirm.html',
                **{'email': email_address, 'token': token}
            )
        })
