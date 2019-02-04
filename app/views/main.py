from flask import Blueprint, render_template, redirect, url_for

from app.core.auth import is_user_logged

home_blueprint = Blueprint('main', __name__)


@home_blueprint.route('/')
def login():
    if is_user_logged():
        return redirect(url_for('customer.dashboard'))

    return render_template('login.html')
