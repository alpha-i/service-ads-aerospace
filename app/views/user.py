import logging

from flask import Blueprint, g, request, abort, url_for

from app.core.auth import requires_access_token, is_valid_email_for_company, requires_admin_permissions
from app.services.user import generate_confirmation_token, confirm_token
from app.core.content import ApiResponse
from app.core.utils import parse_request_data
from app import services
from app.core.models import User

user_blueprint = Blueprint('user', __name__)


@user_blueprint.route('/', methods=['GET'])
@requires_access_token
def show_current_user_info():
    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        context=g.user
    )
    return response()


@user_blueprint.route('/register', methods=['POST'])
@requires_admin_permissions
@parse_request_data
def register():
    email = g.json.get('email')
    password = g.json.get('password')

    assert email and password, abort(400, 'Please specify a user email and password')

    company = services.company.get_for_email(email)
    if not company:
        logging.warning("No company could be found for %s", email)
        abort(400, f"No company could be found for {email}")

    if not is_valid_email_for_company(email, company):
        logging.warning("Invalid email %s for company: %s", email, company.domain)
        abort(401, f"Invalid email {email} for company: {company.domain}")

    user = services.user.get_by_email(email)
    if user is not None:
        abort(400, 'Cannot register an existing user!')

    user = User(email=email, confirmed=False, company_id=company.id, password=password)
    user = services.user.insert(user)

    confirmation_token = generate_confirmation_token(user.email)
    logging.info("Confirmation token for %s: %s", user.email, confirmation_token)

    # Only admins can create users for now
    #services.email.send_confirmation_email(user.email, confirmation_token)

    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        next=url_for('main.login'),
        status_code=201,
        context={
            'email': user.email,
            'id': user.id,
            'confirmation_token': confirmation_token
        }
    )

    return response()


@user_blueprint.route('/confirm/<string:token>')
def confirm(token):
    email = confirm_token(token)
    if not email:
        abort(401, 'Unauthorised')

    user = services.user.get_by_email(email)
    if user.confirmed:
        abort(400, 'User was already confirmed')

    user = services.user.confirm(user)
    logging.info("User %s successfully confirmed!", user.email)

    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        template='user/confirmed.html',
        next=url_for('main.login')
    )

    return response()
