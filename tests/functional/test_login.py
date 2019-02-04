from flask import url_for, json

from app.services.user import generate_confirmation_token
from tests.functional.base_test_class import BaseTestClass


class TestLogin(BaseTestClass):

    def setUp(self):
        super(TestLogin, self).setUp()
        self.create_superuser()
        self.login_superuser()
        self.register_company()

    def test_login_mixed_case(self):
        resp = self.client.post(
            url_for('user.register'),
            content_type='application/json',
            data=json.dumps({
                'email': 'TEST_user@email.com',
                'password': self.USER_PASSWORD
            })
        )
        assert resp.status_code == 201
        confirmation_token = generate_confirmation_token('test_user@email.com')

        resp = self.client.get(
            url_for('user.confirm', token=confirmation_token)
        )
        assert resp.status_code == 200

        resp = self.client.post(
            url_for('authentication.login'),
            content_type='application/json',
            data=json.dumps({'email': 'test_user@email.com',
                             'password': self.USER_PASSWORD}),
            headers={'Accept': 'application/json'}
        )

        assert resp.status_code == 200

        resp = self.client.post(
            url_for('authentication.login'),
            content_type='application/json',
            data=json.dumps({'email': 'TEST_USER@email.com',
                             'password': self.USER_PASSWORD}),
            headers={'Accept': 'application/json'}
        )
        assert resp.status_code == 200
