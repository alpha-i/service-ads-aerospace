import logging
import os

from celery.result import AsyncResult
from flask import Blueprint, request, g, url_for, flash, jsonify
from sqlalchemy_pagination import paginate

from app import ApiResponse, services
from app.core.auth import requires_access_token
from app.core.models import TrainingTask
from app.core.utils import handle_error, parse_request_data, merge_dictionaries
from app.entities import TrainingTaskEntity, TaskStatusTypes
from app.entities.datasource import DataSourceConfigurationEntity, DataSourceEntity
from app.tasks.train import train_celery_task

training_blueprint = Blueprint('training', __name__)


@training_blueprint.route('/', methods=['GET'])
@requires_access_token
def list():
    PER_PAGE = 10

    company_id = g.user.company_id
    current_page = int(request.args.get('page', 1))

    query = services.training.filter_by_company_id(TrainingTaskEntity.query, company_id)

    if request.args.get('datasource_config_id') is not None:
        datasource_config_id = request.args.get('datasource_config_id')
        datasource_config_id = -1 if datasource_config_id == '' else int(datasource_config_id)
        query = services.training.filter_by_datasource_configuration_id(query, datasource_config_id)

    pagination = paginate(query, current_page, PER_PAGE)

    training_tasks = pagination.items

    datasource_configurations = services.datasource.get_configuration_by_company_id(company_id)

    training_task_list = TrainingTask.from_models(*training_tasks)

    if request.args.get('valid_only'):
        training_task_list = [task for task in training_task_list if task.status == TaskStatusTypes.successful.value]

    context = {
        'training_task_list': training_task_list,
        'datasource_configurations': datasource_configurations,
        'pagination': pagination,
        'current_page': current_page
    }

    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        context=context,
        template='training/list.html'
    )

    return response()


@training_blueprint.route('/list.json', methods=['GET'])
@requires_access_token
def json_list():
    company_id = g.user.company_id

    query = services.training.filter_by_company_id(TrainingTaskEntity.query, company_id)

    if request.args.get('datasource_config_id') is not None:
        datasource_config_id = request.args.get('datasource_config_id')
        datasource_config_id = -1 if datasource_config_id == '' else int(datasource_config_id)
        query = services.training.filter_by_datasource_configuration_id(query, datasource_config_id)

    query.order_by(TrainingTaskEntity.id.desc())

    training_tasks = query.all()

    datasource_configurations = services.datasource.get_configuration_by_company_id(company_id)

    training_task_list = TrainingTask.from_models(*training_tasks)
    if request.args.get('valid_only'):
        training_task_list = [task for task in training_task_list if task.status == TaskStatusTypes.successful.value]

    context = {
        'training_task_list': training_task_list,
        'datasource_configurations': datasource_configurations,
    }

    return jsonify(context)


@training_blueprint.route('/<string:training_task_code>', methods=['GET'])
@requires_access_token
def detail(training_task_code):
    company_id = g.user.company_id
    training_task_entity = TrainingTaskEntity.get_for_company_id(
        company_id).filter(TrainingTaskEntity.task_code == training_task_code).one_or_none()
    if not training_task_entity:
        return handle_error(404, 'No training task found!')

    context = {
        'training_task': TrainingTask.from_model(training_task_entity)
    }

    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        context=context,
        template='training/detail.html'
    )

    return response()


@training_blueprint.route('/<string:training_task_code>/delete', methods=['POST'])
@requires_access_token
def delete(training_task_code):
    training_task_entity = services.training.get_training_for_task_code(training_task_code)
    if not training_task_entity:
        return handle_error(404, f'No training found for code {training_task_code}')

    # Terminate the running task
    AsyncResult(training_task_code).revoke(terminate=True)
    training_task_entity.delete()

    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        next=url_for('training.list'),
        status_code=200
    )
    flash(f"Training task {training_task_code} has been deleted", category='success')

    return response()


@training_blueprint.route('/', methods=['POST'])
@requires_access_token
@parse_request_data
def submit():
    user_id = g.user.id
    company_id = g.user.company_id
    name = g.json.get('name')
    enable_fft = g.json.get('enable_fft', None)
    downsample_factor = int(g.json.get('downsample_factor'))
    train_iters = int(g.json.get('train_iters'))

    if enable_fft:
        enable_fft = bool(int(enable_fft))

    datasource_configuration_id = g.json.get('datasource_configuration_id')
    parent_training_id = g.json.get('parent_training_id', None)

    if TrainingTaskEntity.query.filter(TrainingTaskEntity.name == name,
                                       TrainingTaskEntity.company_id == company_id).all():
        return handle_error(400, f'Training with name {name} already exists')

    latest_company_configuration = g.user.company.current_configuration

    datasource_configuration = DataSourceConfigurationEntity.query.filter(
        DataSourceConfigurationEntity.company_id == company_id
    ).filter(
        DataSourceConfigurationEntity.id == datasource_configuration_id
    ).one_or_none()

    if not datasource_configuration:
        return handle_error(404, 'No datasource type found!')

    number_of_sensors = datasource_configuration.meta.get('number_of_sensors')

    if not number_of_sensors:
        return handle_error(400, 'No number of sensors specified! Check datasource configuration')

    number_of_timesteps = 784 // number_of_sensors * downsample_factor

    datasources_for_train = DataSourceEntity.get_for_datasource_configuration(datasource_configuration)
    if not datasources_for_train:
        return handle_error(400, f'No valid datasources available for type {datasource_configuration.name}')

    training_task_code = services.detection.generate_task_code()

    training_configuration = services.training.create_training_configuration(
        training_task_code,
        company_id,
        latest_company_configuration.configuration,
        datasource_configuration.meta,
        enable_fft,
        parent_training_id
    )

    updated_training_configuration = add_training_parameters_to_configuration(
        downsample_factor, number_of_timesteps, train_iters, training_configuration
    )


    logging.info(f"created training configuration: {updated_training_configuration}")

    training_task_entity = TrainingTaskEntity(
        company_id=company_id,
        user_id=user_id,
        task_code=training_task_code,
        company_configuration_id=latest_company_configuration.id,
        datasource_configuration_id=datasource_configuration_id,
        datasources=datasources_for_train,
        configuration=updated_training_configuration,
        name=name,
        parent_training_id=int(parent_training_id) if parent_training_id else None)

    training_task_entity.save()

    os.makedirs(training_task_entity.train_data_dir, exist_ok=True)

    services.training.set_task_status(training_task_entity, status=TaskStatusTypes.queued, message='Enqueued')
    train_celery_task.apply_async(
        args=(training_task_entity.task_code,), task_id=training_task_code
    )

    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        context=TrainingTask.from_model(training_task_entity),
        status_code=201,
        next=url_for('training.list')
    )

    return response()


def add_training_parameters_to_configuration(downsample_factor, number_of_timesteps, train_iters, training_configuration):
    modified_training_configuration = {
        'model': {
            'configuration': {
                'model_configuration': {
                    'train_iters': train_iters
                }
            }
        },
        'transformer': {
            'configuration': {
                'number_of_timesteps': number_of_timesteps,
                'downsample_factor': downsample_factor
            }
        }
    }
    updated_training_configuration = merge_dictionaries(
        training_configuration, modified_training_configuration
    )
    return updated_training_configuration
