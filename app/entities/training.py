import logging
import os

from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Table

from app.entities import BaseEntity, TaskStatusTypes
from config import TRAIN_ROOT_FOLDER


training_datasource_association = Table(
    'datasources_to_training_task', BaseEntity.metadata,
    Column('training_task_id', Integer, ForeignKey('training_task.id')),
    Column('data_source_id', Integer, ForeignKey('data_source.id'))
)


class TrainingTaskEntity(BaseEntity):
    __tablename__ = 'training_task'

    id = Column(Integer, autoincrement=True, primary_key=True)
    INCLUDE_ATTRIBUTES = (
        'datasources', 'statuses', 'datasource_configuration', 'company_configuration', 'is_completed',
        'running_time', 'status', 'train_data_location', 'detection_task_list', 'parent_task', 'upload_code',
        'has_fft_enabled'
    )

    datasource_configuration_id = Column(
        ForeignKey('data_source_configuration.id', name='training_task_datasource_configuration_id_fk')
    )
    datasource_configuration = relationship(
        'DataSourceConfigurationEntity', foreign_keys=datasource_configuration_id
    )

    datasources = relationship(
        'DataSourceEntity', secondary=training_datasource_association,
        back_populates='training_task_list'
    )

    name = Column(String(60), unique=True, index=True)

    company_id = Column(ForeignKey('company.id'), nullable=False)
    company = relationship('CompanyEntity', foreign_keys=company_id)

    company_configuration_id = Column(ForeignKey('company_configuration.id'), nullable=False)
    company_configuration = relationship('CompanyConfigurationEntity', foreign_keys=company_configuration_id)

    user_id = Column(ForeignKey('user.id'), nullable=False)
    user = relationship('UserEntity', foreign_keys=user_id)

    statuses = relationship('TrainingTaskStatusEntity', cascade='all, delete-orphan', order_by='TrainingTaskStatusEntity.id')

    task_code = Column(String(60), index=True, unique=True, nullable=False)
    detection_task_list = relationship('DetectionTaskEntity', back_populates='training_task')

    parent_training_id = Column(ForeignKey('training_task.id'), nullable=True)
    parent_task = relationship(
        'TrainingTaskEntity', foreign_keys=parent_training_id, uselist=False,
        remote_side=[id]
        )

    configuration = Column(JSON)

    @property
    def train_data_location(self):
        return os.path.join(TRAIN_ROOT_FOLDER, str(self.company_id), self.task_code, self.task_code)

    @property
    def train_data_dir(self):
        return os.path.join(TRAIN_ROOT_FOLDER, str(self.company_id), self.task_code)

    @classmethod
    def get_for_company_id(cls, company_id):
        return cls.query.filter(cls.company_id == company_id)

    @classmethod
    def get_for_task_code(cls, training_task_code):
        return cls.query.filter(cls.task_code==training_task_code).one_or_none()

    @property
    def status(self):
        if len(self.statuses):
            return self.statuses[-1].state
        return None

    @property
    def is_completed(self):
        return self.status in [TaskStatusTypes.successful.value, TaskStatusTypes.failed.value]

    @property
    def running_time(self):
        if self.statuses:
            start_time = self.statuses[0].last_update
            for status in self.statuses:
                if status.state == TaskStatusTypes.in_progress.value:
                    start_time = status.last_update
                    break

            end_time = self.statuses[-1].last_update
            return (end_time - start_time).seconds

    @property
    def has_fft_enabled(self):
        try:
            return self.configuration['transformer']['configuration']['enable_fft']
        except KeyError:
            return True

    @property
    def training_save_path(self):
        try:
            return self.configuration['model']['configuration']['model_configuration']['save_path']
        except KeyError:
            logging.info("This configuration seems not having the save_path. returning None")


class TrainingTaskStatusEntity(BaseEntity):
    __tablename__ = 'training_task_status'

    training_task_id = Column(Integer, ForeignKey('training_task.id'), nullable=False)
    training_task = relationship('TrainingTaskEntity', back_populates='statuses')

    state = Column(String(), index=True)
    message = Column(String(), nullable=True)
