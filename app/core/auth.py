import logging
from functools import wraps

from flask import request, g, abort, redirect, url_for

from app.core.models import User
from app.entities import UserEntity
from app.entities.customer import UserPermissions


def requires_access_token(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = is_user_logged()
        if isinstance(user, UserEntity):
            g.user = User.from_model(user)
            return fn(*args, **kwargs)
        else:
            if request.accept_mimetypes.best in ['application/html', 'text/html']:
                return redirect(url_for('main.login'))
            else:
                logging.debug("No authorisation supplied")
                abort(401, "Unauthorised")

    return wrapper


def requires_admin_permissions(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = is_user_logged()
        if not user:
            abort(403)
        g.user = user
        if not user.permissions == UserPermissions.ADMIN:
            logging.debug(f"User {user.email} was not allowed an admin action")
            abort(403, 'Only admins can do that!')
        return fn(*args, **kwargs)

    return wrapper


def is_user_logged():
    if 'X-Token' in request.headers:
        token = request.headers['X-Token']
    elif 'token' in request.cookies:
        token = request.cookies.get('token')
    elif request.content_type == 'application/json':
        token = request.json.get('token')
    else:
        logging.debug("No token provided!")
        return None
    if not token:
        logging.debug("No authentication was supplied")
        abort(401, 'Please supply authentication')

    user = UserEntity.verify_auth_token(token)
    return user


def is_valid_email_for_company(email: str, company):
    company_domain = company.domain
    email_domain = email.split('@')[-1]
    return email_domain == company_domain
