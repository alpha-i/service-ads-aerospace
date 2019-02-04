import json

from flask import url_for

from app.services.user import generate_confirmation_token
from tests.functional.base_test_class import BaseTestClass


class TestContentNegotiation(BaseTestClass):
    def setUp(self):
        super().setUp()
        self.create_superuser()

    def test_login_can_deal_with_json_as_default(self):
        self.login_superuser()
        self.register_company()
        self.register_user()
        self.logout()

        resp = self.client.post(
            url_for('authentication.login'),
            content_type='application/json',
            data=json.dumps({'email': self.USER_EMAIL, 'password': self.USER_PASSWORD}),
            headers={'Accept': 'application/json'}
        )

        assert resp.status_code == 200
        assert resp.content_type == 'application/json'
        assert 'token' in resp.json

    def test_login_can_negotiate(self):
        self.login_superuser()
        self.register_company()
        self.register_user()
        self.logout()
        resp = self.client.post(
            url_for('authentication.login'),
            content_type='application/json',
            data=json.dumps({'email': self.USER_EMAIL, 'password': self.USER_PASSWORD}),
            headers={'Accept': 'application/html'}

        )

        assert resp.headers.get('Location') == url_for('customer.dashboard', _external=True)

        resp = self.client.get(
            url_for('authentication.logout'),
            content_type='application/json',  # TODO: changeme! it should accept html requests
            headers={'Accept': 'application/html'}
        )

        assert resp.headers.get('Location') == url_for('main.login', _external=True)

    def test_logout_can_negotiate(self):
        self.login_superuser()
        self.register_company()
        self.register_user()
        self.logout()
        self.login()

        resp = self.client.get(url_for('authentication.logout'))

        assert resp.status_code == 200
        assert resp.headers.get('Set-Cookie') == 'token=; Expires=Thu, 01-Jan-1970 00:00:00 GMT; Path=/'

        self.login()

        resp = self.client.get(url_for('authentication.logout'), headers={'Accept': 'application/html'})

        assert resp.status_code == 302
        assert resp.headers.get('Location') == url_for('main.login', _external=True)

    def test_user_registration_can_render_json(self):
        self.login_superuser()
        self.register_company()

        resp = self.client.post(
            url_for('user.register'),
            content_type='application/json',
            headers={'Accept': 'application/json'},
            data=json.dumps({
                'email': self.USER_EMAIL,
                'password': self.USER_PASSWORD
            })
        )

        assert resp.status_code == 201

    def test_user_registration_can_redirect(self):
        self.login_superuser()
        self.register_company()

        resp = self.client.post(
            url_for('user.register'),
            content_type='application/json',
            headers={'Accept': 'application/html'},
            data=json.dumps({
                'email': self.USER_EMAIL,
                'password': self.USER_PASSWORD
            })
        )

        assert resp.status_code == 302

    def test_company_registration_can_negotiate(self):
        self.login_superuser()
        resp = self.client.post(
            url_for('company.register'),
            content_type='application/json',
            data=json.dumps(
                {'name': 'ACME Inc',
                 'domain': 'email.com'}
            )

        )
        assert resp.status_code == 201

        resp = self.client.post(
            url_for('company.register'),
            content_type='application/json',
            headers={'Accept': 'application/html'},
            data=json.dumps(
                {'name': 'ACME Inc',
                 'domain': 'email.it'}
            )
        )
        assert resp.status_code == 201

    def test_user_confirmation(self):
        self.login_superuser()
        self.register_company()

        # first register a user
        resp = self.client.post(
            url_for('user.register'),
            content_type='application/json',
            data=json.dumps({
                'email': self.USER_EMAIL,
                'password': self.USER_PASSWORD
            })
        )
        assert resp.status_code == 201
        confirmation_token = generate_confirmation_token('test_user@email.com')

        resp = self.client.get(
            url_for('user.confirm', token=confirmation_token),
            headers={'Accept': 'application/html'}
        )
        assert resp.status_code == 200
        assert resp.headers.get('Location') == url_for('main.login', _external=True)
