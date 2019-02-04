import enum
import os

import pandas as pd
from sqlalchemy import Column, Integer, ForeignKey, String, Enum, JSON, UniqueConstraint
from sqlalchemy import event
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound

from app.database import local_session_scope
from app.entities import BaseEntity, CustomerActionEntity, Actions
from app.entities.training import training_datasource_association
from config import HDF5_STORE_INDEX, UPLOAD_ROOT_FOLDER


class UploadTypes(enum.Enum):
    FILESYSTEM = 'filesystem'
    BLOBSTORE = 'blobstore'


class LabelTypes(enum.Enum):
    NORMAL = 'normal'
    ABNORMAL = 'abnormal'


class DataSourceConfigurationEntity(BaseEntity):
    __tablename__ = 'data_source_configuration'
    __table_args__ = (UniqueConstraint('company_id', 'name', name='_datasource_config_name_company_uc'),)

    company_id = Column(ForeignKey('company.id', name='data_source_company_id_fk'))
    company = relationship('CompanyEntity', foreign_keys=company_id)

    name = Column(String(60), index=True, nullable=False)
    meta = Column(JSON)

    # Could be a json with
    # {
    #     "sample_rate": 1024,
    #     "n_sensors": 8,
    #     ...
    # }

    @classmethod
    def get_for_company_id(cls, company_id):
        return cls.query.filter(cls.company_id == company_id)

    @classmethod
    def get_for_id(cls, id):
        return cls.query.filter(cls.id == id).one_or_none()


class DataSourceEntity(BaseEntity):
    INCLUDE_ATTRIBUTES = ('type', 'meta', 'location', 'datasource_configuration', 'is_part_of_training_set')

    __tablename__ = 'data_source'
    __table_args__ = (UniqueConstraint('company_id', 'name', name='_datasource_company_id_name_uc'),)

    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    user = relationship('UserEntity', foreign_keys=user_id)

    company_id = Column(Integer, ForeignKey('company.id'), nullable=False)
    company = relationship('CompanyEntity', foreign_keys=company_id)

    datasource_configuration_id = Column(
        ForeignKey('data_source_configuration.id',
                   name='data_source_datasource_configuration_id_fkey')
    )
    datasource_configuration = relationship(
        'DataSourceConfigurationEntity', foreign_keys=datasource_configuration_id
    )

    label = Column(Enum(LabelTypes), index=True, nullable=True)  # is null until someone flags it explicitly
    name = Column(String(), index=True)
    upload_code = Column(String(), index=True)
    type = Column(Enum(UploadTypes), index=True)
    filename = Column(String(), nullable=False)
    meta = Column(JSON)

    detection_task_list = relationship(
        'DetectionTaskEntity', back_populates='datasource', cascade='all, delete-orphan'
    )

    training_task_list = relationship(
        'TrainingTaskEntity', back_populates='datasources', secondary=training_datasource_association
    )

    @property
    def location(self):
        return os.path.join(UPLOAD_ROOT_FOLDER, str(self.company_id), self.filename)

    def get_file(self):
        with pd.HDFStore(self.location) as hdf_store:
            dataframe = hdf_store[HDF5_STORE_INDEX]
            return dataframe

    @staticmethod
    def get_for_user(user_id):
        return DataSourceEntity.query.filter(DataSourceEntity.user_id == str(user_id)).all()

    @staticmethod
    def get_by_upload_code(upload_code):
        try:
            return DataSourceEntity.query.filter(DataSourceEntity.upload_code == upload_code).one()
        except NoResultFound:
            return None

    @staticmethod
    def generate_filename(upload_code, original_filename):
        return f"{upload_code}_{original_filename}"

    @staticmethod
    def get_for_datasource_configuration(datasource_configuration):
        return DataSourceEntity.query.filter(
            DataSourceEntity.datasource_configuration_id == datasource_configuration.id
        ).all()

    @property
    def is_part_of_training_set(self):
        if self.training_task_list:
            return True
        return False


def update_user_action(mapper, connection, self):
    action = CustomerActionEntity(
        company_id=self.company_id,
        user_id=self.user_id,
        action=Actions.FILE_UPLOAD
    )
    with local_session_scope() as session:
        session.add(action)


event.listen(DataSourceEntity, 'after_insert', update_user_action)
