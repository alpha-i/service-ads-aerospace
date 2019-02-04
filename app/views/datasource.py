import logging

from flask import Blueprint, request, url_for, g, flash, jsonify, Response
from sqlalchemy_pagination import paginate

from app import services
from app.core.auth import requires_access_token
from app.core.content import ApiResponse
from app.core.utils import generate_upload_code, handle_error, parse_request_data
from app.entities import TaskStatusTypes, TrainingTaskEntity
from app.entities.datasource import DataSourceConfigurationEntity, LabelTypes, DataSourceEntity
from app.interpreters.dataview import DataView
from config import DEFAULT_VIEW_TIME_RESAMPLE_RULE

datasource_blueprint = Blueprint('datasource', __name__)


@datasource_blueprint.route('/', methods=['GET'])
@requires_access_token
def list():
    PER_PAGE = 10
    company_id = g.user.company_id
    if not g.user.company.current_configuration:
        return handle_error(404, 'No company configuration found, please provide one.')

    upload_manager = services.company.get_upload_manager(g.user.company.current_configuration)

    current_page = int(request.args.get('page', 1))

    query = services.datasource.filter_by_company_id(DataSourceEntity.query, company_id)

    pagination = paginate(query, current_page, PER_PAGE)

    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        context={'datasources': pagination.items,
                 'pagination': pagination,
                 'current_page': current_page,
                 'allowed_extensions': ','.join([".{}".format(ext) for ext in upload_manager.allowed_extensions]),
                 'max_file_size': 2147483648,
                 'datasource_types': DataSourceConfigurationEntity.get_for_company_id(company_id).all()
                 },
        template='datasource/list.html'
    )
    return response()


@datasource_blueprint.route('/configuration', methods=['GET'])
@requires_access_token
def list_configurations():
    company_id = g.user.company_id
    datasource_configurations = DataSourceConfigurationEntity.get_for_company_id(company_id).all()
    return jsonify(datasource_configurations)


@datasource_blueprint.route('/configuration', methods=['POST'])
@requires_access_token
@parse_request_data
def submit_configuration():
    company_id = g.user.company_id
    configuration_name = g.json.get('name')  # TODO: use a schema for this
    configuration_metadata = g.json.get('meta')

    if not configuration_metadata or not configuration_name:
        return handle_error(400, 'Error: You must specify name and meta values')

    new_datasource_configuration = DataSourceConfigurationEntity(
        company_id=company_id,
        name=configuration_name,
        meta=configuration_metadata
    )

    new_datasource_configuration.save()

    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        next=url_for('datasource.list'),
        context={'datasource_config': new_datasource_configuration},
        status_code=201
    )

    return response()


@datasource_blueprint.route('/configuration/<int:datasource_configuration_id>', methods=['GET'])
@requires_access_token
def get_configuration(datasource_configuration_id):
    company_id = g.user.company_id
    datasource_configuration = DataSourceConfigurationEntity.get_for_id(datasource_configuration_id)
    if not datasource_configuration:
        return handle_error(404, 'No datasource configuration found')
    if not datasource_configuration.company_id == company_id:
        return handle_error(403, 'Unauthorised')

    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        context=datasource_configuration
    )

    return response()


@datasource_blueprint.route('/<string:upload_code>', methods=['GET'])
@requires_access_token
def detail(upload_code):
    datasource = services.datasource.get_by_upload_code(upload_code)

    if not datasource:
        logging.debug(f"No flight was found for code {upload_code}")
        return handle_error(404, 'No flight found!')
    if not datasource.company_id == g.user.company_id:
        return handle_error(403, "Unauthorised")

    query = TrainingTaskEntity.query
    query = services.training.filter_by_datasource_configuration_id(query, datasource.datasource_configuration_id)
    query = services.training.filter_by_company_id(query, datasource.company_id)

    query = services.training.filter_by_status(query, TaskStatusTypes.successful)
    query.order_by(TrainingTaskEntity.id.desc())

    training_task_list = query.all()

    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        context={
            'datasource': datasource,
            'label_types': {member.name: member.value for member in LabelTypes},
            'detection_task_list': services.detection.get_task_for_datasource_id(datasource.id),
            'training_task_list': training_task_list
        },
        template='datasource/detail.html'
    )

    return response()


@datasource_blueprint.route('/label', methods=['POST'])
@requires_access_token
@parse_request_data
def save_label():
    upload_code = g.json.get('upload_code')
    datasource_label = g.json.get('datasource_label')

    datasource_entity = DataSourceEntity.query.filter(DataSourceEntity.upload_code == upload_code).one_or_none()

    if not datasource_entity:
        logging.debug(f"No datasource was found for code {upload_code}")
        return handle_error(404, 'No data source found!')
    if not datasource_entity.company_id == g.user.company_id:
        return handle_error(403, "Unauthorised")

    if datasource_label:
        try:
            label_type = LabelTypes[datasource_label]
            datasource_entity.label = label_type
        except KeyError:
            return handle_error(404, f'Invalid label {datasource_label} for datasource')
    else:
        datasource_entity.label = None

    datasource_entity.update()

    datasource = services.datasource.get_by_upload_code(upload_code)

    flash(f"Flight label has been set to '{datasource_label}'", category='success')

    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        next=url_for('datasource.detail', upload_code=upload_code),
        context={'datasource': datasource},
        status_code=201
    )

    return response()


@datasource_blueprint.route('/<string:upload_code>/data', methods=['GET'])
def data(upload_code):
    datasource = services.datasource.get_by_upload_code(upload_code=upload_code)
    data_view = DataView.create_from_datasource(datasource)
    data_view.wrap_columns_name('Sensor {}')
    normalize = True if request.args.get('normalize') else False

    return jsonify(data_view.to_dict(DEFAULT_VIEW_TIME_RESAMPLE_RULE, normalize))


@datasource_blueprint.route('/<string:upload_code>/csv', methods=['GET'])
def data_csv(upload_code):
    datasource = services.datasource.get_by_upload_code(upload_code=upload_code)
    data_view = DataView.create_from_datasource(datasource)
    data_view.wrap_columns_name('Sensor {}')
    normalize = True if request.args.get('normalize') else False

    return Response(
        data_view.to_csv(DEFAULT_VIEW_TIME_RESAMPLE_RULE, normalize),
        mimetype='text/plain'
    )


@datasource_blueprint.route('/', methods=['POST'])
@requires_access_token
@parse_request_data
def upload():
    user = g.user
    company = user.company
    datasource_name = g.json.get('name')
    if not datasource_name:
        return handle_error(400, "Please provide a name for the data upload")

    if services.datasource.datasource_name_exists(datasource_name):
        return handle_error(400, f"A data source for {datasource_name} already exists")

    datasource_type_id = g.json.get('datasource_type_id')
    if not datasource_type_id:
        return handle_error(400, "Please provide a datasource type id!")

    datasource_type = DataSourceConfigurationEntity.get_for_id(datasource_type_id)
    if not datasource_type:
        return handle_error(404, f"No datasource type found for {datasource_type_id}")

    if not len(request.files):
        logging.debug("No file was uploaded")
        return handle_error(400, "No file Provided!")

    company_configuration = company.current_configuration
    uploaded_file = request.files['upload']

    if not company_configuration:
        uploaded_file.close()
        return handle_error(400, f"{company.name} cannot upload data yet, please contact support.")

    upload_manager = services.company.get_upload_manager(company_configuration)

    try:
        uploaded_dataframe = upload_manager.validate(uploaded_file, datasource_type_id)
    except Exception as e:
        message = f"Data validation has failed: {str(e)}"
        return handle_error(400, message)

    upload_code = generate_upload_code()

    try:
        datasource = services.datasource.save_datasource(
            datasource_name, company.id, datasource_type_id, upload_code, upload_manager, uploaded_dataframe, user
        )
    except Exception as e:
        upload_manager.cleanup(upload_code)
        return handle_error(400, str(e))

    flash("Flight uploaded successfully.", category='success')

    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        next=url_for('datasource.detail', upload_code=upload_code),
        context={'datasource': datasource},
        status_code=201
    )

    return response()


@datasource_blueprint.route('/delete/<string:datasource_id>', methods=['POST'])
@requires_access_token
def delete(datasource_id):
    upload_manager = services.company.get_upload_manager(g.user.company.current_configuration)
    datasource = services.datasource.get_by_upload_code(datasource_id)

    if datasource.is_part_of_training_set:
        return handle_error(400, f"Flight {datasource.name} is part of training set, cannot be deleted")

    services.datasource.delete(datasource)

    upload_manager.cleanup(datasource.location)

    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        next=url_for('datasource.list'),
        status_code=200
    )
    flash(f"Flight {datasource.name} version {datasource_id} has been deleted", category='success')
    return response()
