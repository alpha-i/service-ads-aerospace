import abc
import logging

import pandas as pd
from flask import json

from app.core.jsonencoder import CustomJSONEncoder
from app.core.schemas import (
    UserSchema, CompanySchema, DetectionTaskSchema, DataSourceSchema,
    CompanyConfigurationSchema, DetectionTaskStatusSchema, DetectionResultSchema, DiagnosticTaskSchema,
    DiagnosticTaskStatusSchema, DiagnosticResultSchema, DataSourceConfigurationSchema, TrainingTaskSchema,
    TrainingTaskStatusSchema)
from app.entities import (
    UserEntity, CompanyEntity, DetectionTaskEntity, DetectionResultEntity, DataSourceEntity,
    CompanyConfigurationEntity, DetectionTaskStatusEntity,
    DiagnosticTaskEntity, DiagnosticTaskStatusEntity, DiagnosticResultEntity, TrainingTaskEntity,
    TrainingTaskStatusEntity)
from app.entities.datasource import DataSourceConfigurationEntity
from config import HDF5_STORE_INDEX


class EntityCreationException(Exception):
    pass


class BaseModel(metaclass=abc.ABCMeta):
    SCHEMA = None
    MODEL = None

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

    @classmethod
    def from_model(cls, model):
        if model is None:
            return None

        schema = cls.SCHEMA()
        data, errors = schema.loads(json.dumps(model.to_dict(), cls=CustomJSONEncoder))
        if errors:
            logging.debug("{} error loading json from database {}".format(cls.__name__, errors))

        entity = cls()
        setattr(entity, '_model', model)

        for key, value in data.items():
            setattr(entity, key, value)
        return entity

    @classmethod
    def from_models(cls, *models):
        return [cls.from_model(model) for model in models]

    def to_model(self):
        model = self.MODEL()

        for key, value in self.__dict__.items():
            if value:
                setattr(model, key, value)
        return model

    def refresh(self):
        for key, value in self._model.to_dict().items():
            if not getattr(self, key, None):
                setattr(self, key, value)

    def load(self, **kwargs):
        return self.SCHEMA().load(kwargs)

    def dump(self):
        return self.SCHEMA().dumps(self)

    def update(self):

        for key, value in self.__dict__.items():
            if key == '_model':
                continue

            setattr(self._model, key, value)

        self._model.update()

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.__dict__}>"


class User(BaseModel):
    SCHEMA = UserSchema
    MODEL = UserEntity


class Company(BaseModel):
    SCHEMA = CompanySchema
    MODEL = CompanyEntity


class DetectionTask(BaseModel):
    SCHEMA = DetectionTaskSchema
    MODEL = DetectionTaskEntity


class DetectionTaskStatus(BaseModel):
    SCHEMA = DetectionTaskStatusSchema
    MODEL = DetectionTaskStatusEntity


class DataSource(BaseModel):
    SCHEMA = DataSourceSchema
    MODEL = DataSourceEntity

    def get_file(self):
        with pd.HDFStore(self.location) as hdf_store:
            dataframe = hdf_store[HDF5_STORE_INDEX]
            return dataframe


class DetectionResult(BaseModel):
    SCHEMA = DetectionResultSchema
    MODEL = DetectionResultEntity


class CompanyConfiguration(BaseModel):
    SCHEMA = CompanyConfigurationSchema
    MODEL = CompanyConfigurationEntity


class DiagnosticTask(BaseModel):
    SCHEMA = DiagnosticTaskSchema
    MODEL = DiagnosticTaskEntity


class DiagnosticTaskStatus(BaseModel):
    SCHEMA = DiagnosticTaskStatusSchema
    MODEL = DiagnosticTaskStatusEntity


class DiagnosticResult(BaseModel):
    SCHEMA = DiagnosticResultSchema
    MODEL = DiagnosticResultEntity


class DataSourceConfiguration(BaseModel):
    SCHEMA = DataSourceConfigurationSchema
    MODEL = DataSourceConfigurationEntity


class TrainingTask(BaseModel):
    SCHEMA = TrainingTaskSchema
    MODEL = TrainingTaskEntity


class TrainingTaskStatus(BaseModel):
    SCHEMA = TrainingTaskStatusSchema
    MODEL = TrainingTaskStatusEntity
