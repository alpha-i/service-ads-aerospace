import pandas as pd
from datetime import datetime, date, timedelta
from enum import Enum

import enum
import numpy
from alphai_watson.detective import DetectionResult, DiagnosticResult
from flask.json import JSONEncoder
from sqlalchemy.ext.declarative import DeclarativeMeta
from sqlalchemy_pagination import Page


class CustomJSONEncoder(JSONEncoder):

    def default(self, obj):
        from app.core.models import BaseModel
        if issubclass(obj.__class__, BaseModel):
            data, _ = obj.SCHEMA().dump(obj)
            return data
        if isinstance(obj.__class__, DeclarativeMeta):
            return obj.to_dict()
        if issubclass(obj.__class__, Enum):
            return obj.name
        if isinstance(obj, datetime):
            return obj.strftime('%Y-%m-%dT%H:%M:%S%z')
        if isinstance(obj, date):
            return obj.strftime('%Y-%m-%d')
        if isinstance(obj, numpy.float32):
            return obj.tolist()
        if isinstance(obj, numpy.int64):
            return obj.tolist()
        if isinstance(obj, numpy.ndarray):
            return obj.tolist()
        if isinstance(obj, timedelta):
            return str(obj)
        if isinstance(obj, DetectionResult):
            return {
                'data': obj.data,
                'original_sample_rate': obj.original_sample_rate,
                'timesteps_per_chunk': obj._number_timesteps_in_chunk
            }

        if isinstance(obj, DiagnosticResult):
            return {
                    'chunk_index': obj.chunk_index,
                    'chunk_timedelta': obj.chunk_timedelta,
                    'diagnostic': obj.result,
                    'original': obj.original_chunk,
                    'synthetic': obj.synthetic_chunk
            }

        if isinstance(obj, enum.EnumMeta):
            return {member.name: member.value for member in obj}

        if isinstance(obj, Page):
            return {
                "items": obj.items,
                "has_previous": obj.has_previous,
                "previous_page": obj.previous_page,
                "has_next": obj.has_next,
                "next_page": obj.next_page,
                "total": obj.total,
                "pages": obj.pages
            }

        if isinstance(obj, pd.Timedelta):
            return str(obj)

        return super(CustomJSONEncoder, self).default(obj)
