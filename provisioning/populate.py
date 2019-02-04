import os

import yaml
import logging

import requests

from app.services.superuser import create_admin

logging.basicConfig(level=logging.INFO)

THIS_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

configuration_file = os.path.join(THIS_DIRECTORY, 'configuration.yml')
configuration = yaml.load(open(configuration_file, 'r'))


admin_username = configuration["admin"]["username"]
admin_password = configuration["admin"]["password"]

APP_URL = 'http://localhost:5000/{}'

request_headers = {
    'Accept': 'application/json',
    'Content-Type': 'application/json'
}

create_admin(admin_username, admin_password)
# login superuser
logging.info("Login Superuser to retrieve Token")

response = requests.post(
    APP_URL.format('auth/login'),
    json={"email": admin_username, "password": admin_password},
    headers=request_headers
)
admin_token = response.json().get('token')
request_headers.update({'X-Token': admin_token})

company = configuration["company"]
domain_name = company["domain_name"]
company_name = company["company_name"]
company_configuration = company["configuration"]
logging.info(f"Register default company {company_name}")

response = requests.post(
    APP_URL.format('company/register'),
    json={"name": company_name, "domain": domain_name},
    headers=request_headers
)

response_body = response.json()
company_id = response_body.get("id")


logging.info(f"Update company configuration {company_name} id {company_id}")
response = requests.post(
    APP_URL.format(f"company/configuration/{company_id}"),
    json=company_configuration,
    headers=request_headers
)


user_email = configuration["user"]["email"]
user_password = configuration["user"]["password"]

logging.info(f"Create User name {user_email}")
create_user_response = requests.post(
    APP_URL.format('user/register'),
    headers=request_headers,
    json={"email": user_email, "password": user_password}
)

confirmation_token = create_user_response.json().get('confirmation_token')

confirm_user_response = requests.get(
    APP_URL.format(f'user/confirm/{confirmation_token}'),
    headers=request_headers
)

del request_headers["X-Token"]

logging.info("User Login")
response = requests.post(
    APP_URL.format(f"auth/login"),
    headers=request_headers,
    json={"email": user_email, "password": user_password}
)

user_token = response.json().get('token')

request_headers.update({'X-Token': user_token})
datasource_config = configuration["datasource_configuration"]

logging.info("Create Datasource Configuration")
response = requests.post(
    APP_URL.format(f"datasource/configuration"),
    headers=request_headers,
    json=datasource_config
)


