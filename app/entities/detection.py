from sqlalchemy import event, Column, String, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound

from app.database import db_session, local_session_scope
from app.entities import BaseEntity, CustomerActionEntity, Actions, TaskStatusTypes


class DetectionTaskEntity(BaseEntity):
    __tablename__ = 'detection_task'

    INCLUDE_ATTRIBUTES = ('status', 'statuses', 'is_completed',
                          'datasource', 'running_time', 'datasource_id',
                          'is_time_domain', 'is_frequency_domain')

    name = Column(String(60), nullable=False)

    company_id = Column(ForeignKey('company.id'), nullable=False)
    company = relationship('CompanyEntity', foreign_keys=company_id)

    configuration_id = Column(ForeignKey('company_configuration.id'), nullable=False)
    configuration = relationship('CompanyConfigurationEntity', foreign_keys=configuration_id)

    user_id = Column(ForeignKey('user.id'), nullable=False)
    user = relationship('UserEntity', foreign_keys=user_id)

    statuses = relationship('DetectionTaskStatusEntity', cascade='all, delete-orphan', order_by='DetectionTaskStatusEntity.id')

    upload_code = Column(String(60), nullable=False, index=True)
    task_code = Column(String(60), nullable=False, unique=True, index=True)

    datasource_id = Column(Integer, ForeignKey('data_source.id'), nullable=False)
    datasource = relationship('DataSourceEntity', back_populates='detection_task_list', single_parent=True)

    training_task_id = Column(Integer, ForeignKey('training_task.id'), nullable=False)
    training_task = relationship('TrainingTaskEntity', foreign_keys=training_task_id)

    detection_result = relationship('DetectionResultEntity', uselist=False, back_populates='detection_task',
                                    single_parent=True,
                                    cascade='all, delete-orphan')

    diagnostic_task = relationship('DiagnosticTaskEntity', cascade='all, delete-orphan')

    @staticmethod
    def get_by_upload_code(upload_code):
        try:
            detection_task_entity = DetectionTaskEntity.query.filter(
                DetectionTaskEntity.upload_code == upload_code).one()
            return detection_task_entity
        except NoResultFound:
            return None

    @staticmethod
    def get_by_task_code(task_code):
        try:
            detection_task_entity = DetectionTaskEntity.query.filter(
                DetectionTaskEntity.task_code == task_code).one()
            return detection_task_entity
        except NoResultFound:
            return None

    @staticmethod
    def get_by_datasource_id(datasource_id, ):
        return DetectionTaskEntity.query.filter(
            DetectionTaskEntity.datasource_id == datasource_id
        ).order_by(DetectionTaskEntity.last_update.desc()).all()

    @staticmethod
    def get_by_user_id(user_id):
        return DetectionTaskEntity.query.filter(DetectionTaskEntity.user_id == user_id).all()

    @staticmethod
    def get_successful_by_company_id(company_id):
        return DetectionTaskEntity.query.filter(
            DetectionTaskEntity.company_id == company_id,
            DetectionTaskEntity.statuses.any(state=TaskStatusTypes.successful.value)
        ).all()

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
            end_time = self.statuses[-1].last_update
            return (end_time - start_time).seconds

    @property
    def is_frequency_domain(self):
        return self.training_task.has_fft_enabled

    @property
    def is_time_domain(self):
        return not self.training_task.has_fft_enabled


class DetectionTaskStatusEntity(BaseEntity):
    __tablename__ = 'detection_task_status'

    detection_task_id = Column(Integer, ForeignKey('detection_task.id'), nullable=False)
    detection_task = relationship('DetectionTaskEntity', back_populates='statuses')
    state = Column(String(), index=True)
    message = Column(String(), nullable=True)


class DetectionResultEntity(BaseEntity):
    __tablename__ = 'detection_result'

    company_id = Column(Integer, ForeignKey('company.id'), nullable=False)
    company = relationship('CompanyEntity', back_populates='detection_results')

    upload_code = Column(String(60), index=True)
    task_code = Column(String(60), unique=True, index=True)
    result = Column(JSONB)

    detection_task_id = Column(Integer, ForeignKey('detection_task.id'), nullable=False)
    detection_task = relationship('DetectionTaskEntity', back_populates='detection_result',
                                  single_parent=True,
                                  cascade='all, delete-orphan')

    @staticmethod
    def get_for_task_code(task_code):
        try:
            detection_result_entity = DetectionResultEntity.query.filter(
                DetectionResultEntity.task_code == task_code).one()
            db_session.refresh(detection_result_entity)
            return detection_result_entity

        except NoResultFound:
            return None


def update_user_action(mapper, connection, self):
    action = CustomerActionEntity(
        company_id=self.company_id,
        user_id=self.user_id,
        action=Actions.DETECTION_STARTED
    )
    with local_session_scope() as session:
        session.add(action)


event.listen(DetectionTaskEntity, 'after_insert', update_user_action)
