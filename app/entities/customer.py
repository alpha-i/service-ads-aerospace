import enum
import logging

from itsdangerous import (
    TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired
)
from passlib.apps import custom_app_context as pwd_context
from sqlalchemy import (event, Column, String, JSON, ForeignKey, Boolean, Enum)
from sqlalchemy.orm import relationship, validates
from sqlalchemy.orm.exc import NoResultFound

from app.database import db_session, local_session_scope
from app.entities import BaseEntity
from config import SECRET_KEY


class Actions(enum.Enum):
    FILE_UPLOAD = 'FILE_UPLOAD'
    DETECTION_STARTED = 'DETECTION_STARTED'
    CONFIGURATION_UPDATE = 'CONFIGURATION_UPDATE'


class UserPermissions(enum.Enum):
    USER = 'USER'
    ADMIN = 'ADMIN'


class CompanyEntity(BaseEntity):
    __tablename__ = 'company'

    INCLUDE_ATTRIBUTES = ('current_configuration', 'current_datasource', 'actions',
                          'detection_results', 'data_sources', 'detection_tasks')

    name = Column(String, nullable=False)
    logo = Column(String)
    domain = Column(String, nullable=False)
    profile = Column(JSON)

    detection_tasks = relationship('DetectionTaskEntity', back_populates='company')
    detection_results = relationship('DetectionResultEntity', back_populates='company')

    diagnostic_tasks = relationship('DiagnosticTaskEntity', back_populates='company')
    diagnostic_results = relationship('DiagnosticResultEntity', back_populates='company')

    actions = relationship('CustomerActionEntity', back_populates='company')
    configuration = relationship('CompanyConfigurationEntity', back_populates='company', order_by="desc(CompanyConfigurationEntity.id)")
    data_sources = relationship('DataSourceEntity', back_populates='company', order_by="desc(DataSourceEntity.id)")
    users = relationship('UserEntity', back_populates='company')

    @staticmethod
    def get_for_email(email):
        domain = email.split('@')[-1]
        try:
            logging.info('Searching for a company %s', domain)
            company = CompanyEntity.query.filter(CompanyEntity.domain == domain).one()
        except NoResultFound:
            return None
        return company

    @staticmethod
    def get_for_domain(domain):
        try:
            company = CompanyEntity.query.filter(CompanyEntity.domain == domain).one()
        except NoResultFound:
            return None
        return company

    @staticmethod
    def get_by_id(company_id):
        try:
            company = CompanyEntity.query.filter(CompanyEntity.id == company_id).one()
        except NoResultFound:
            return None
        return company

    @property
    def current_configuration(self):
        if len(self.configuration):
            return self.configuration[0]


class UserEntity(BaseEntity):
    __tablename__ = 'user'

    INCLUDE_ATTRIBUTES = ('actions', 'company')
    EXCLUDE_ATTRIBUTES = ('password_hash',)

    email = Column(String(32), index=True)
    password_hash = Column(String(128))

    data_sources = relationship('DataSourceEntity', back_populates='user')

    company_id = Column(ForeignKey('company.id'), nullable=False)
    company = relationship('CompanyEntity', foreign_keys=company_id)

    profile = relationship('UserProfileEntity', uselist=False)
    permissions = Column(Enum(UserPermissions), default=UserPermissions.USER)

    confirmed = Column(Boolean, default=False)

    def hash_password(self, password):
        self.password_hash = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)

    def generate_auth_token(self, expiration=3600):  # TODO: change this!
        s = Serializer(SECRET_KEY, expires_in=expiration)
        return s.dumps({'id': self.id})

    @validates('email')
    def convert_email_to_lowercase(self, key, value):
        return value.lower()

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(SECRET_KEY)
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None
        except BadSignature:
            return None

        user = db_session.query(UserEntity).get(data['id'])
        db_session.refresh(user)
        db_session.commit()
        return user

    @staticmethod
    def get_user_by_email(email):
        email = email.lower()
        try:
            return UserEntity.query.filter(UserEntity.email == email).one()
        except NoResultFound:
            return None


class CustomerActionEntity(BaseEntity):
    __tablename__ = 'customer_action'

    company_id = Column(ForeignKey('company.id'), nullable=False)
    company = relationship('CompanyEntity', foreign_keys=company_id)
    user_id = Column(ForeignKey('user.id'), nullable=False)
    user = relationship('UserEntity', foreign_keys=user_id)
    action = Column(Enum(Actions))


class UserProfileEntity(BaseEntity):
    __tablename__ = 'user_profile'

    user_id = Column(ForeignKey('user.id'), nullable=False)
    user = relationship('UserEntity', foreign_keys=user_id)


class CompanyConfigurationEntity(BaseEntity):
    __tablename__ = 'company_configuration'

    company_id = Column(ForeignKey('company.id'), nullable=False)
    company = relationship('CompanyEntity', foreign_keys=company_id)
    user_id = Column(ForeignKey('user.id'), nullable=False)
    user = relationship('UserEntity', foreign_keys=user_id)
    configuration = Column(JSON)  # TODO: Decide what the configuration should look like

    @staticmethod
    def get_by_id(id):
        try:
            configuration = CompanyConfigurationEntity.query.filter(CompanyConfigurationEntity.id == id).one()
        except NoResultFound:
            return None
        return configuration

    @staticmethod
    def get_by_company_id(company_id):
        return CompanyConfigurationEntity.query.filter(
            CompanyConfigurationEntity.company_id == company_id).all()


def update_user_action(mapper, connection, self):
    action = CustomerActionEntity(
        company_id=self.company_id,
        user_id=self.user_id,
        action=Actions.CONFIGURATION_UPDATE
    )
    with local_session_scope() as session:
        session.add(action)


event.listen(CompanyConfigurationEntity, 'after_insert', update_user_action)
