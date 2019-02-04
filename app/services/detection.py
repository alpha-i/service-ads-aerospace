import logging
import uuid

import numpy as np
from alphai_watson.detective import DetectionResult as DetectiveDetectionResult
from attribdict import AttribDict

from app import services
from app.core.models import DetectionTask, DetectionResult, DetectionTaskStatus
from app.entities import DetectionTaskEntity, DetectionResultEntity, TaskStatusTypes


def get_task_by_code(task_code):
    model = DetectionTaskEntity.get_by_task_code(task_code)
    return DetectionTask.from_model(model)


def get_task_for_datasource_id(datasource_id):
    models = DetectionTaskEntity.get_by_datasource_id(datasource_id)
    return DetectionTask.from_models(*models)


def get_result_by_code(task_code):
    model = DetectionResultEntity.get_for_task_code(task_code)
    return DetectionResult.from_model(model)


def get_tasks_by_company_id(company_id):
    return DetectionTaskEntity.query.filter(DetectionTaskEntity.company_id == company_id).order_by(
        DetectionTaskEntity.created_at.desc()).all()


def insert_task(detection_task):
    model = detection_task.to_model()
    model.save()
    return DetectionTask.from_model(model)


def update_task(detection_task):
    model = detection_task._model
    for k, v in detection_task.__dict__.items():
        try:
            setattr(model, k, v)
        except AttributeError:
            logging.debug(f"CANNOT SET {k} to {v}")
    model.update()
    return DetectionTask.from_model(model)


def insert_result(detection_result):
    model = detection_result.to_model()
    model.save()
    return DetectionResult.from_model(model)


def insert_status(status):
    model = status.to_model()
    model.save()
    return DetectionTaskStatus.from_model(model)


def set_task_status(task, status, message=None):
    task_status = services.detection.insert_status(
        DetectionTaskStatus(
            detection_task_id=task.id,
            state=status.value,
            message=message
        )
    )
    return task_status


def create_detection_task(task_name, upload_code, task_code, datasource_id, company_id, user_id, training_task_id,
                          configuration_id):
    task = insert_task(
        DetectionTask(
            name=task_name,
            upload_code=upload_code,
            company_id=company_id,
            task_code=task_code,
            user_id=user_id,
            training_task_id=training_task_id,
            datasource_id=datasource_id,
            configuration_id=configuration_id,
        )
    )
    set_task_status(
        task, TaskStatusTypes.queued,
        message="Task has been enqueued")
    return task


def generate_task_code():
    return str(uuid.uuid4())


def trigger_detection(detection_name, datasource, training_task, user_id):
    task_code = services.detection.generate_task_code()
    detection_task = create_detection_task(
        task_name=detection_name,
        upload_code=datasource.upload_code,
        task_code=task_code,
        datasource_id=datasource.id,
        company_id=datasource.company_id,
        user_id=user_id,
        training_task_id=training_task.id,
        configuration_id=training_task.company_configuration_id,
    )

    return detection_task


def delete(detection_task):
    model = detection_task._model
    model.delete()


def create_watson_detection_result_from_dictionary(detection_result_json):
    detection_result = AttribDict(detection_result_json)

    return DetectiveDetectionResult(
        np.array(detection_result.data),
        detection_result.timesteps_per_chunk,
        detection_result.original_sample_rate
    )


def load_calibration_values(detection_task):
    task_code = detection_task.task_code
    task = services.detection.get_task_by_code(task_code)
    calibration = task._model.training_task.configuration.get('calibration')
    if calibration:
        k = calibration.get('k')
        x0 = calibration.get('x0')
        anomaly_prior = calibration.get('anomaly_prior')
    else:
        k = None
        x0 = None
        anomaly_prior = None
    return k, x0, anomaly_prior


def filter_by_company_id(query, company_id):
    return query.filter(DetectionTaskEntity.company_id == company_id).order_by(DetectionTaskEntity.created_at.desc())
