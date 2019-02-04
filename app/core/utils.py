import importlib
import logging
import string
import uuid
from copy import deepcopy
from functools import wraps

from flask import request, g, json, url_for, redirect, abort, flash

from app.core.auth import is_user_logged
from app.core.jsonencoder import CustomJSONEncoder
from config import ALLOWED_EXTENSIONS


def parse_request_data(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if request.is_json:
            g.json = request.json
        elif request.form:
            g.json = {
                key: value[0] if len(value) == 1 else value
                for key, value in request.form.lists()
            }
        return fn(*args, **kwargs)

    return wrapper


def json_reload(json_as_a_dict):
    return json.loads(json.dumps(json_as_a_dict, cls=CustomJSONEncoder))


def allowed_extension(filename):
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS


def generate_upload_code():
    return str(uuid.uuid4())


def import_class(name):
    components = name.split('.')
    mod = importlib.import_module(".".join(components[:-1]))
    return getattr(mod, components[-1])


def calculate_referrer_url():
    """
    Returns the referer. if not specified, it will fallback to the login page
    if the user is not logged in, otherwise it will go to the dashboard home.

    :return:
    """
    default_route = 'customer.dashboard' if is_user_logged() else 'main.login'
    return request.referrer or url_for(default_route)


def handle_error(code, message, *args, **kwargs):
    """
    Helper function around the abort functionality of flask.
    It returns a redirect response with a flash message if the request is json, * or not specified.

    :param int code: the error code
    :param str message: the error message
    :param list args: argument to pass to the abort function
    :param {} kwargs: kwargs to pass to the abort function

    :return HttpException or RedirectResponse :
    """
    logging.error(message)
    if request.accept_mimetypes.best in ['application/json', '*/*', None]:
        abort(code, message, args, *kwargs)

    flash(message, category='warning')
    return redirect(calculate_referrer_url())


class MissingFieldsStringFormatter(string.Formatter):
    def __init__(self, missing='~'):
        self.missing = missing

    def get_field(self, field_name, args, kwargs):
        # Handle missing fields
        try:
            return super().get_field(field_name, args, kwargs)
        except (KeyError, AttributeError):
            return None, field_name

    def format_field(self, value, spec):
        if value is None:
            return self.missing
        else:
            return super().format_field(value, spec)


def merge_dictionaries(source, target):
    merged = deepcopy(source)
    for key in target:
        if key in merged and isinstance(merged[key], dict):
            if isinstance(target[key], dict):
                merged[key] = merge_dictionaries(merged[key], target[key])
            else:
                merged[key].update(target[key])
        else:
            merged[key] = target[key]
    return merged
