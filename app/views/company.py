import logging

from flask import Blueprint, g, abort, request

from app import services
from app.core.auth import requires_access_token, requires_admin_permissions
from app.core.content import ApiResponse
from app.core.models import Company, CompanyConfiguration
from app.core.schemas import ModelConfigurationSchema
from app.core.utils import parse_request_data, json_reload, handle_error

company_blueprint = Blueprint('company', __name__)


@company_blueprint.route('/', methods=['GET'])
@requires_access_token
def show_current_company_info():
    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        context=g.user.company
    )
    return response()


@company_blueprint.route('/actions', methods=['GET'])
@requires_access_token
def list_customer_actions():
    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        context=g.user.company.actions
    )

    return response()


@company_blueprint.route('/register', methods=['POST'])
@parse_request_data
@requires_admin_permissions
def register():
    company_name = g.json.get('name')
    domain = g.json.get('domain')

    if not (company_name and domain):
        logging.debug("Company name and/or domain weren't supplied")
        abort(400, 'Request error: please specify company name and company domain.')

    existing_company = services.company.get_for_domain(domain)
    if existing_company:
        logging.debug(f"Cannot recreate an existing company: {domain}")
        abort(400, 'Unable to create existing company')

    company = Company(name=company_name, domain=domain)
    company = services.company.insert(company)

    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        context=company,
        status_code=201
    )

    return response()


@company_blueprint.route('/configuration', methods=['GET'])
@requires_access_token
def current_configuration():
    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        context=g.user.company.current_configuration
    )

    return response()


@company_blueprint.route('/configuration/<int:company_id>', methods=['GET'])
@requires_admin_permissions
def configuration_detail(company_id):
    configuration = services.company.get_configurations_by_company_id(company_id)
    if not configuration:
        logging.debug(f"No configuration found for company id {company_id}")
        abort(404, 'No such configuration found')
    return ApiResponse(
        content_type=request.accept_mimetypes.best,
        context=configuration
    )()


@company_blueprint.route('/configuration/<int:company_id>', methods=['POST'])
@requires_admin_permissions
@parse_request_data
def configuration_update(company_id):
    company = services.company.get_by_id(company_id)
    if not company:
        return handle_error(404, "No company could be found!")
    configuration_request = g.json
    data, errors = ModelConfigurationSchema().load(configuration_request)

    if errors or not data:
        logging.debug(f"Invalid configuration supplied: {str(errors)}")
        return abort(400, f"Invalid configuration: {str(errors)}")

    configuration = CompanyConfiguration(
        company_id=company_id,
        user_id=g.user.id,
        configuration=json_reload(data)
    )

    configuration = services.company.insert_configuration(configuration)

    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        context=configuration.configuration,
        status_code=201
    )

    return response()
