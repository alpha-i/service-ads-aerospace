import datetime
import logging

from flask import Blueprint, g, url_for, request

from app import services
from app.core.auth import requires_access_token
from app.core.content import ApiResponse
from app.core.utils import parse_request_data, handle_error
from config import TOKEN_EXPIRATION

authentication_blueprint = Blueprint('authentication', __name__)


@authentication_blueprint.route('/login', methods=['POST'])
@parse_request_data
def login():
    email = g.json.get('email')
    password = g.json.get('password')

    user = services.user.get_by_email(email)
    if not user:
        logging.debug(f"No user found for {email}")
        return handle_error(401, 'Incorrect user or password')

    if not services.user.verify_password(user, password):
        logging.warning(f"Incorrect password for {email}")
        return handle_error(401, 'Incorrect user or password')

    if not user.confirmed:
        logging.warning(f"User {user.email} hasn't been confirmed!")
        return handle_error(401, f'Please confirm user {user.email} first')

    token = services.user.generate_auth_token(user, expiration=TOKEN_EXPIRATION)
    ascii_token = token.decode('ascii')

    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        next=url_for('customer.dashboard'),
        context={'token': ascii_token}
    )

    response.set_cookie(
        'token', ascii_token,
        expires=datetime.datetime.now() + datetime.timedelta(minutes=TOKEN_EXPIRATION)
    )

    return response()


@authentication_blueprint.route('/logout')
@requires_access_token
def logout():
    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        next=url_for('main.login')
    )
    response.set_cookie('token', '', expires=0)

    return response()
