from itsdangerous import (TimedJSONWebSignatureSerializer as Serializer, URLSafeTimedSerializer)

from app.core.models import User
from app.entities import UserEntity
from config import SECRET_KEY


def generate_auth_token(user, expiration=3600):
    s = Serializer(SECRET_KEY, expires_in=expiration)
    return s.dumps({'id': user.id})


def verify_token(token):
    user = UserEntity.verify_auth_token(token)
    return User.from_model(user)


def get_by_email(email):
    user = UserEntity.get_user_by_email(email)
    return User.from_model(user)


def verify_password(user, password):
    return user._model.verify_password(password)


def insert(user):
    model = user.to_model()
    model.hash_password(password=model.password)
    model.save()
    return User.from_model(model)


def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    return serializer.dumps(email)


def confirm_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(SECRET_KEY)
    try:
        email = serializer.loads(token, max_age=expiration)
    except:
        return False
    return email


def confirm(user):
    model = user._model
    model.confirmed = True
    model.save()
    return User.from_model(model)
