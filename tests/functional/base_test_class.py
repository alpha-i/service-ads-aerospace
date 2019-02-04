import json
import os

from flask import url_for
from flask_testing import TestCase

from app.database import db_session, engine
from app.entities.base import EntityDeclarativeBase
from app.services.superuser import create_admin
from app.services.user import generate_confirmation_token
from config import SUPERUSER_EMAIL, SUPERUSER_PASSWORD
from tests.test_app import APP


class BaseTestClass(TestCase):
    TESTING = True

    SUPERUSER_EMAIL = SUPERUSER_EMAIL
    SUPERUSER_PASSWORD = SUPERUSER_PASSWORD
    USER_EMAIL = 'test_user@email.com'
    USER_PASSWORD = 'password'

    COMPANY_CONFIGURATION_JSON = """
    {
      "datasource_class": "tests.mock_detective.MockDataSource",
      "datasource_interpreter": "FlightDatasourceInterpreter",
      "model": {
        "class_name": "tests.mock_detective.MockleRick",
        "configuration": {}
      },
      "transformer": {
        "class_name": "tests.mock_detective.MockTransformer",
        "configuration": {
          "number_of_sensors": 8,
          "number_of_timesteps": 10
        }
      },
      "upload_manager": "FlightUploadManager"
    }
    """
    COMPANY_ID = 2
    COMPANY_CONFIGURATION = json.loads(COMPANY_CONFIGURATION_JSON)

    def create_app(self):
        return APP

    def setUp(self):

        db_session.close()
        db_session.remove()
        EntityDeclarativeBase.metadata.drop_all(engine)
        EntityDeclarativeBase.metadata.create_all(engine)

    def tearDown(self):
        from app.entities.datasource import DataSourceEntity
        uploads = [datasource.location for datasource in DataSourceEntity.query.all()]
        for upload in uploads:
            os.remove(upload)
        db_session.close()
        db_session.remove()

    def create_superuser(self):
        create_admin(self.SUPERUSER_EMAIL, self.SUPERUSER_PASSWORD)

    def login_superuser(self):
        resp = self.client.post(
            url_for('authentication.login'),
            content_type='application/json',
            data=json.dumps({'email': self.SUPERUSER_EMAIL, 'password': self.SUPERUSER_PASSWORD}),
            headers={'Accept': 'application/json'}
        )
        assert resp.status_code == 200
        self.token = resp.json['token']

    def register_company(self):
        resp = self.client.post(
            url_for('company.register'),
            content_type='application/json',
            data=json.dumps(
                {'name': 'ACME Inc',
                 'domain': 'email.com'}
            )
        )
        assert resp.status_code == 201

    def set_company_configuration(self):
        resp = self.client.post(
            url_for('company.configuration_update', company_id=self.COMPANY_ID),  # company 1 is the super-company...
            data=json.dumps(self.COMPANY_CONFIGURATION),
            content_type='application/json',
            headers={'Accept': 'application/json'}
        )

        assert resp.status_code == 201

    def register_user(self):
        # we won't accept a registration for a user not in the company...
        resp = self.client.post(
            url_for('user.register'),
            content_type='application/json',
            data=json.dumps({
                'email': 'test_user@email.co.uk',
                'password': 'password'
            })
        )

        assert resp.status_code == 400

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

        # we won't accept a login for a unconfirmed user...
        resp = self.client.post(
            url_for('authentication.login'),
            content_type='application/json',
            data=json.dumps({'email': self.USER_EMAIL, 'password': self.USER_PASSWORD})
        )
        assert resp.status_code == 401

        # we now require a confirmation for the user
        resp = self.client.get(
            url_for('user.confirm', token=confirmation_token)
        )
        assert resp.status_code == 200

    def login(self):
        # we now require a token authorization for the endpoints
        resp = self.client.post(
            url_for('authentication.login'),
            content_type='application/json',
            data=json.dumps({'email': self.USER_EMAIL, 'password': self.USER_PASSWORD}),
            headers={'Accept': 'application/json'}
        )

        assert resp.status_code == 200

        self.token = resp.json['token']

    def create_datasource_configuration(self):
        datasource_config = {
            'name': 'Datasource Config',
            'meta': {'sample_rate': 1024, 'number_of_sensors': 8, }
        }
        resp = self.client.post(
            url_for('datasource.submit_configuration'),
            data=json.dumps(datasource_config),
            content_type='application/json',
            headers={'Accept': 'application/json'}
        )

        assert resp.status_code == 201
        self.datasource_configuration_id = resp.json['datasource_config']['id']

    def logout(self):
        resp = self.client.get(
            url_for('authentication.logout')
        )
        assert resp.status_code == 200
