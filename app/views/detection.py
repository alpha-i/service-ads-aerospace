import logging

import pandas as pd
from flask import Blueprint, jsonify, url_for, g, request, abort, Response, flash
from sqlalchemy_pagination import paginate

import app.services.training
from app import services
from app.core.auth import requires_access_token
from app.core.content import ApiResponse
from app.core.utils import parse_request_data, handle_error
from app.entities import DetectionTaskEntity
from app.interpreters.dataview import DataView
from app.tasks.detect import detect_celery_task
from config import DEFAULT_VIEW_TIME_RESAMPLE_RULE

detection_blueprint = Blueprint('detection', __name__)


@detection_blueprint.route('/<string:upload_code>', methods=['POST'])
@requires_access_token
@parse_request_data
def submit(upload_code):
    user_id = g.user.id
    training_task_code = g.json.get('training_task_code')
    detection_name = g.json.get('name')

    training_task = app.services.training.get_training_for_task_code(training_task_code)

    datasource = services.datasource.get_by_upload_code(upload_code)

    detection_task = services.detection.trigger_detection(
        detection_name, datasource, training_task, user_id
    )

    # This should actually live inside the trigger detection function...
    detect_celery_task.apply_async(
        (detection_task.task_code,)
    )

    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        next=url_for('detection.detail', task_code=detection_task.task_code),
        context={
            'task_code': detection_task.task_code,
            'task_status': url_for('detection.detail', task_code=detection_task.task_code, _external=True),
            'result': url_for('detection.result', task_code=detection_task.task_code, _external=True)
        }
    )

    return response()


@detection_blueprint.route('/', methods=['GET'])
@requires_access_token
def list():
    PER_PAGE = 10

    current_page = int(request.args.get('page', 1))

    query = services.detection.filter_by_company_id(DetectionTaskEntity.query, g.user.company.id)

    pagination = paginate(query, current_page, PER_PAGE)
    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        template='detection/list.html',
        context={
            'detection_task_list': pagination.items,
            'pagination': pagination,
            'current_page': current_page
        }
    )

    return response()


@detection_blueprint.route('/<string:task_code>', methods=['GET'])
@requires_access_token
def detail(task_code):
    detection = services.detection.get_task_by_code(task_code)
    diagnostic_task = services.diagnostic.get_task_by_code(task_code)
    training_task = app.services.training.get_training_for_id(detection.training_task_id)

    if not detection:
        logging.debug(f"No task found for code {task_code}")
        return handle_error(404, 'No task found!')
    if not detection.company_id == g.user.company_id:
        return handle_error(403, "Unauthorised")

    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        context={'detection': detection, 'diagnostic': diagnostic_task, 'training_task': training_task},
        template='detection/detail.html'
    )

    return response()


@detection_blueprint.route('/<string:task_code>/delete', methods=['POST'])
@requires_access_token
def delete(task_code):
    detection_task = services.detection.get_task_by_code(task_code)
    services.detection.delete(detection_task)

    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        next=url_for('detection.list'),
        status_code=200
    )
    flash(f"Task version {task_code} has been deleted", category='success')
    return response()


@detection_blueprint.route('/result', methods=['GET'])
@requires_access_token
def get_results():
    return jsonify(g.user.company.detection_results)


@detection_blueprint.route('/<string:task_code>/result', methods=['GET'])
@requires_access_token
def result(task_code):
    detection_result = services.detection.get_result_by_code(task_code)
    if not detection_result:
        logging.debug(f"No result was found for task code {task_code}")
        abort(404, 'No result found!')

    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        context=detection_result
    )

    return response()


@detection_blueprint.route('/<string:task_code>/result/data', methods=['GET'])
@requires_access_token
def result_data(task_code):
    detection_result = services.detection.get_result_by_code(task_code)

    if not detection_result:
        logging.debug(f"No result was found for task code {task_code}")
        data_view = DataView(pd.DataFrame(), sample_rate=1)
    else:
        detection_task = services.detection.get_task_by_code(task_code)
        k, x0, anomaly_prior = services.detection.load_calibration_values(detection_task)

        detection_result = services.detection.create_watson_detection_result_from_dictionary(detection_result.result)

        data_view = DataView.create_from_detection_result(detection_result, k, x0, anomaly_prior)
        data_view.wrap_columns_name('Anomaly')

    normalize = True if request.args.get('normalize') else False

    return Response(
        data_view.to_csv(DEFAULT_VIEW_TIME_RESAMPLE_RULE, normalize),
        mimetype='text/plain'
    )


@detection_blueprint.route('/<string:task_code>/result/download', methods=['GET'])
@requires_access_token
def download_detection_csv(task_code):
    detection_task = services.detection.get_task_by_code(task_code)
    detection_result = services.detection.get_result_by_code(task_code)

    if not detection_result:
        return handle_error(404, "No detection found!")

    if not detection_result.company_id == g.user.company_id:
        return handle_error(403, "Unauthorised")

    k, x0, anomaly_prior = services.detection.load_calibration_values(detection_task)

    detection_result = services.detection.create_watson_detection_result_from_dictionary(detection_result.result)
    data_view = DataView.create_from_detection_result(detection_result, k, x0, anomaly_prior)

    data_view.wrap_columns_name('Sensor {}')

    return Response(
        data_view.to_csv(DEFAULT_VIEW_TIME_RESAMPLE_RULE, normalize=True),
        mimetype='text/csv',
        headers={"Content-disposition": "attachment; filename={}.csv".format(
            detection_task.name
        )})
