from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound

from app.entities import BaseEntity, TaskStatusTypes


class DiagnosticTaskEntity(BaseEntity):
    __tablename__ = 'diagnostic_task'

    INCLUDE_ATTRIBUTES = ( 'statuses', 'status', 'running_time', 'is_completed',
                           'diagnostic_result', 'is_time_domain', 'is_frequency_domain')

    detection_task_id = Column(ForeignKey('detection_task.id'))
    detection_task = relationship('DetectionTaskEntity', foreign_keys=detection_task_id,
                                  back_populates='diagnostic_task')

    company_id = Column(ForeignKey('company.id'))
    company = relationship('CompanyEntity', foreign_keys=company_id)

    statuses = relationship('DiagnosticTaskStatusEntity', cascade='all, delete-orphan', order_by='DiagnosticTaskStatusEntity.id')

    datasource_id = Column(ForeignKey('data_source.id'))
    datasource = relationship('DataSourceEntity', foreign_keys=datasource_id,
                              single_parent=True)

    upload_code = Column(String(60), nullable=False, index=True)
    task_code = Column(String(60), nullable=False, index=True)

    diagnostic_result = relationship('DiagnosticResultEntity', uselist=False, back_populates='diagnostic_task',
                                     single_parent=True,
                                     cascade='all, delete-orphan')

    @staticmethod
    def get_for_company(company_id):
        return DiagnosticTaskEntity.query.filter(DiagnosticTaskEntity.company_id == company_id).all()

    @staticmethod
    def get_for_detection_task_code(detection_task_code):
        try:
            diagnostic_task = DiagnosticTaskEntity.query.filter(
                DiagnosticTaskEntity.task_code == detection_task_code).one()
            return diagnostic_task
        except NoResultFound:
            return None

    @property
    def status(self):
        if self.statuses:
            return self.statuses[-1].state

    @property
    def is_completed(self):
        return self.status in [
            TaskStatusTypes.successful.value, TaskStatusTypes.failed.value
        ]

    @property
    def running_time(self):
        if self.statuses:
            start_time = self.statuses[0].last_update
            end_time = self.statuses[-1].last_update
            return (end_time - start_time).seconds

    @property
    def is_frequency_domain(self):
        return self.detection_task.is_frequency_domain

    @property
    def is_time_domain(self):
        return self.detection_task.is_time_domain


class DiagnosticTaskStatusEntity(BaseEntity):
    __tablename__ = 'diagnostic_task_status'

    diagnostic_task_id = Column(ForeignKey('diagnostic_task.id'), nullable=False)
    diagnostic_task = relationship('DiagnosticTaskEntity', back_populates='statuses', foreign_keys=diagnostic_task_id)
    state = Column(String(), index=True)
    message = Column(String(), nullable=True)


class DiagnosticResultEntity(BaseEntity):
    __tablename__ = 'diagnostic_result'

    INCLUDE_ATTRIBUTES = ('company_id', 'diagnostic_task_id', 'upload_code', 'task_code', 'result')

    company_id = Column(ForeignKey('company.id'), nullable=False)
    company = relationship('CompanyEntity', back_populates='diagnostic_results')

    upload_code = Column(String(60), index=True)
    task_code = Column(String(60), unique=True, index=True)

    result = Column(JSONB)

    diagnostic_task_id = Column(ForeignKey('diagnostic_task.id'), nullable=False)
    diagnostic_task = relationship('DiagnosticTaskEntity', foreign_keys=diagnostic_task_id,
                                   single_parent=True,
                                   cascade='all, delete-orphan')
