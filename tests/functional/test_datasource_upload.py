import os

from flask import url_for

from tests.functional.base_test_class import BaseTestClass

HERE = os.path.join(os.path.dirname(__file__))


class TestDataSourceUpload(BaseTestClass):
    TESTING = True

    def setUp(self):
        super().setUp()
        self.create_superuser()
        self.login_superuser()
        self.register_company()
        self.register_user()
        self.set_company_configuration()
        self.create_datasource_configuration()
        self.logout()

    def test_upload_file_for_customer(self):
        self.login()
        with open(os.path.join(HERE, '../resources/test_good_file_fight.hd5'), 'rb') as test_upload_file:
            resp = self.client.post(
                url_for('datasource.upload'),
                content_type='multipart/form-data',
                data={
                    'upload': (test_upload_file, 'test_good_file_fight.hd5'), 'name': 'first_flight',
                     'datasource_type_id': self.datasource_configuration_id
                     },
                headers={'Accept': 'application/json'}
            )

            assert resp.status_code == 201
            assert resp.json['datasource']['user_id'] == 2

        with open(os.path.join(HERE, '../resources/test_good_file_fight.hd5'), 'rb') as updated_data_file:
            resp = self.client.post(
                url_for('datasource.upload'),
                content_type='multipart/form-data',
                data={
                    'upload': (updated_data_file, 'test_good_file_fight.hd5'),
                    'name': 'second_flight',
                    'datasource_type_id': self.datasource_configuration_id
                },
                headers={'Accept': 'application/html'}
            )

        assert resp.status_code == 302  # in order to redirect to the dashboard

    def test_user_can_delete_a_datasource(self):
        self.login()
        with open(os.path.join(HERE, '../resources/test_good_file_fight.hd5'), 'rb') as test_upload_file:
            resp = self.client.post(
                url_for('datasource.upload'),
                content_type='multipart/form-data',
                data={
                    'upload': (test_upload_file, 'test_good_file_fight.hd5'), 'name': 'to_delete_flight',
                    'datasource_type_id': self.datasource_configuration_id
                },
                headers={'Accept': 'application/html'}
            )
            assert resp.status_code == 302  # in order to redirect to the dashboard
            assert resp.json
            original_upload_code = resp.json['datasource']['upload_code']

        resp = self.client.post(
            url_for('datasource.delete', datasource_id=original_upload_code),
            content_type='application/json',
            headers={'Accept': 'application/html'}
        )

        assert resp.status_code == 302
