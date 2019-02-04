import re

from attribdict import AttribDict
from marshmallow import Schema, fields, validates, ValidationError
from marshmallow_enum import EnumField

from app.entities.customer import UserPermissions
from app.entities.datasource import UploadTypes, LabelTypes


class BaseModelSchema(Schema):
    id = fields.Integer(allow_none=True)
    created_at = fields.DateTime(allow_none=True)
    last_update = fields.DateTime(allow_none=True)

    @property
    def dict_class(self):
        return AttribDict


class DetectionResultSchema(BaseModelSchema):
    company_id = fields.Integer(required=True)
    detection_task_id = fields.Integer(required=True)
    upload_code = fields.String(required=True)
    task_code = fields.String(allow_none=True)
    result = fields.Raw()


class DetectionTaskStatusSchema(BaseModelSchema):
    state = fields.String()
    message = fields.String(allow_none=True)


class ConfigurableObjectSchema(Schema):
    class_name = fields.String(required=True)
    configuration = fields.Dict(required=True)


class ModelConfigurationSchema(Schema):
    upload_manager = fields.String(required=True)
    datasource_interpreter = fields.String(required=True)
    datasource_class = fields.String(required=True)
    model = fields.Nested(ConfigurableObjectSchema, many=False)
    transformer = fields.Nested(ConfigurableObjectSchema, many=False)


class CompanyConfigurationSchema(BaseModelSchema):
    company_id = fields.Integer()
    configuration = fields.Nested(ModelConfigurationSchema, many=False)


class DetectionTaskSchema(BaseModelSchema):
    name = fields.String()
    company_id = fields.Integer()
    upload_code = fields.String()
    task_code = fields.String()
    status = fields.String(allow_none=True)
    is_completed = fields.Boolean()
    datasource_id = fields.Integer()
    datasource = fields.Nested('DataSourceSchema')
    configuration_id = fields.Integer()
    training_task_id = fields.Integer()
    configuration = fields.Nested(CompanyConfigurationSchema)
    statuses = fields.Nested(DetectionTaskStatusSchema, many=True, default=[])
    running_time = fields.TimeDelta(allow_none=True)
    is_frequency_domain = fields.Bool()
    is_time_domain = fields.Bool()


class CustomerActionSchema(BaseModelSchema):
    user_id = fields.Integer()
    action = fields.String()


class CompanySchema(BaseModelSchema):
    name = fields.String()
    domain = fields.String()
    current_configuration = fields.Nested(CompanyConfigurationSchema, default=None, allow_none=True)
    datasources = fields.Nested('DataSourceSchema', many=True, default=[], load_from='data_sources',
                                dump_to='data_sources')
    current_datasource = fields.Nested('DataSourceSchema', allow_none=True)
    actions = fields.Nested(CustomerActionSchema, many=True, default=[])
    detection_tasks = fields.Nested(DetectionTaskSchema, many=True, default=[])
    detection_results = fields.Nested(DetectionResultSchema, many=True, default=[])

    @validates('domain')
    def validate_domain(self, value):
        if not re.match(r'^([a-z0-9]+(-[a-z0-9]+)*\.)+[a-z]{2,}$', value):
            raise ValidationError("Invalid domain name")


class UserSchema(BaseModelSchema):
    email = fields.Email()
    confirmed = fields.Boolean(allow_none=True)
    company_id = fields.Integer()
    company = fields.Nested(CompanySchema, many=False)
    permissions = EnumField(UserPermissions)


class DiagnosticTaskStatusSchema(BaseModelSchema):
    state = fields.String()
    message = fields.String(allow_none=True)


class DiagnosticResultSchema(BaseModelSchema):
    company_id = fields.Integer()
    diagnostic_task_id = fields.Integer()

    task_code = fields.String()
    upload_code = fields.String()

    result = fields.Raw()


class DiagnosticTaskSchema(BaseModelSchema):
    detection_task_id = fields.Integer()
    company_id = fields.Integer()

    task_code = fields.String()
    upload_code = fields.String()

    statuses = fields.Nested(DiagnosticTaskStatusSchema, many=True, default=[])
    status = fields.String(allow_none=True)
    is_completed = fields.Boolean()
    datasource_id = fields.Integer()
    running_time = fields.TimeDelta(allow_none=True)

    diagnostic_result = fields.Nested(DiagnosticResultSchema, allow_none=True)

    is_frequency_domain = fields.Bool()
    is_time_domain = fields.Bool()


class DataSourceConfigurationSchema(BaseModelSchema):
    company_id = fields.Integer()
    name = fields.String()
    meta = fields.Dict()


class TrainingTaskStatusSchema(BaseModelSchema):
    training_task_id = fields.Integer()
    state = fields.String()
    message = fields.String()


class TrainingTaskSchema(BaseModelSchema):
    datasource_configuration_id = fields.Integer()
    datasource_configuration = fields.Nested(DataSourceConfigurationSchema)
    datasources = fields.Nested('DataSourceSchema', many=True, only=('id', 'name', 'upload_code'))
    name = fields.String()
    company_id = fields.Integer()
    company_configuration_id = fields.Integer()
    company_configuration = fields.Nested(CompanyConfigurationSchema)
    user_id = fields.Integer()
    statuses = fields.Nested(TrainingTaskStatusSchema, many=True)
    task_code = fields.String()
    configuration = fields.Raw()
    is_completed = fields.Boolean()
    running_time = fields.TimeDelta(allow_none=True)
    status = fields.String(allow_none=True)
    detection_task_list = fields.Nested(
        'DetectionTaskSchema', many=True,
        only=('id', 'name', 'task_code', 'upload_code', 'created_at', 'statuses', 'datasource')
    )

    parent_training_id = fields.Integer(allow_none=True)
    parent_task = fields.Nested('self', only=('id', 'name', 'task_code'), allow_none=True, many=None)

    has_fft_enabled = fields.Bool()


class DataSourceSchema(BaseModelSchema):
    user_id = fields.Integer()
    company_id = fields.Integer()
    datasource_configuration_id = fields.Integer(allow_none=True)
    datasource_configuration = fields.Raw(allow_none=True)  # TODO: Schema for this
    upload_code = fields.String()
    type = EnumField(UploadTypes)
    location = fields.String()
    filename = fields.String()
    label = EnumField(LabelTypes, allow_none=True)
    name = fields.String()
    meta = fields.Dict()
    is_part_of_training_set = fields.Boolean()
