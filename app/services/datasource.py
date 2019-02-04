import os

from app.core.models import DataSource
from app.entities import DataSourceEntity
from app.entities.datasource import UploadTypes, DataSourceConfigurationEntity


def get_by_upload_code(upload_code):
    model = DataSourceEntity.get_by_upload_code(upload_code)
    if not model:
        return None
    return DataSource.from_model(model)


def datasource_name_exists(datasource_name):
    count = DataSourceEntity.query.filter(DataSourceEntity.name == datasource_name).count()
    if count > 0:
        return True
    return False


def generate_filename(upload_code, filename):
    return DataSourceEntity.generate_filename(upload_code, filename)


def insert(upload):
    model = upload.to_model()
    model.save()
    return DataSource.from_model(model)


def delete(datasource):
    model = datasource._model
    model.delete()


def update(datasource):
    model = datasource.to_model()
    model.save()


def get_dataframe(datasource):
    model = DataSourceEntity.get_by_upload_code(datasource.upload_code)
    return model.get_file()


def get_configuration_by_id(id):
    model = DataSourceConfigurationEntity.get_for_id(id)
    return model


def get_configuration_by_company_id(company_id):
    return DataSourceConfigurationEntity.get_for_company_id(company_id).all()


def save_datasource(name, company_id, datasource_configuration_id, upload_code, upload_manager, uploaded_dataframe,
                    user):
    datasource_configuration = get_configuration_by_id(datasource_configuration_id)
    if not datasource_configuration:
        raise Exception(f"No datasource configuration available for {datasource_configuration_id}")
    saved_path = upload_manager.store(uploaded_dataframe, company_id, upload_code)

    upload = DataSource(
        user_id=user.id,
        name=name,
        datasource_configuration_id=datasource_configuration.id,
        company_id=user.company_id,
        upload_code=upload_code,
        type=UploadTypes.FILESYSTEM,
        filename=os.path.basename(saved_path),
        meta=datasource_configuration.meta
    )
    datasource = insert(upload)
    return datasource


def filter_by_company_id(query, company_id):
    return query.filter(DataSourceEntity.company_id == company_id).order_by(DataSourceEntity.created_at.desc())


def filter_by_datasource_configuration_id(query, datasource_configuration_id):
    return query.filter(DataSourceEntity.datasource_configuration_id == datasource_configuration_id)


def filter_by_label(query, label):
    return query.filter(DataSourceEntity.label == label)
