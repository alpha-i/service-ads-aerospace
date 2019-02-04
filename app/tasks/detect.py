import logging

import app.services.training
from app import services
from app.core.models import DetectionResult
from app.core.utils import json_reload
from app.entities import TaskStatusTypes
from app.tasks.base import BaseDBTask

logging.basicConfig(level=logging.DEBUG)


class DetectTask(BaseDBTask):
    name = 'detection_task'

    def run(self, task_code):
        detection_task = services.detection.get_task_by_code(task_code)
        upload_code = detection_task.upload_code
        uploaded_file = services.datasource.get_by_upload_code(upload_code)

        if not uploaded_file:
            logging.warning("No upload could be found for code %s", upload_code)
            return

        if not detection_task:
            logging.warning("No detection task could be found for code %s", task_code)
            return

        company_id = uploaded_file.company_id
        company = services.company.get_by_id(company_id)

        services.detection.set_task_status(
            detection_task, TaskStatusTypes.in_progress,
            message='Detection in progress'
        )

        # In order to make the detection work, the normalizer of the datasource
        # has to be initialized by looking at the training data at least once.
        # in order to do that, I have to load the training datasource, and execute the get_train_data

        # get the training task
        training_task = app.services.training.get_training_for_id(detection_task.training_task_id)
        training_task = app.services.training.update_root_folder_in_model_config(training_task)

        transformer = self._create_and_initialize_transformer(training_task)

        # we get the detection datasource
        datasource_class = services.watson.get_datasource_class_from_company_configuration(
            company.current_configuration)

        # we initialized it with the training datasource transfomer
        datasource = datasource_class(uploaded_file.location, transformer)

        training_task = services.detective.set_correct_load_path_for_detection_and_diagnose(training_task)

        logging.debug(training_task.configuration)
        detective = services.detective.create_detective_from_configuration(training_task)

        samples = list(datasource.get_test_data('NORMAL'))
        logging.debug(f"Preparing detection on test data: {samples[0].data}")
        detection = detective.detect(samples[0])

        detection_result = DetectionResult(
            company_id=company_id,
            upload_code=detection_task.upload_code,
            task_code=task_code,
            result=json_reload(detection),
            detection_task_id=detection_task.id
        )

        services.detection.insert_result(detection_result)

        services.detection.set_task_status(detection_task, TaskStatusTypes.successful,
                                           message=f'Task {task_code} has finished')

        services.diagnostic.trigger_diagnostic(detection_task, upload_code)
        return

    def _create_and_initialize_transformer(self, training_task):
        transformer = services.watson.create_transformer_from_configuration(training_task)
        training_datasource = app.services.training.create_training_datasource(training_task, transformer)
        # with this function we trigger the normalizer's viewing of the train data
        training_datasource.get_train_data('NORMAL')
        return training_datasource.transformer


    def on_failure(self, exc, task_id, args, kwargs, einfo):
        task_code = args[0]
        detection_task = services.detection.get_task_by_code(task_code)
        logging.debug(f'Task {task_code} raised exception: {einfo.exception!r}\n{einfo.traceback!r}')
        services.detection.set_task_status(detection_task, TaskStatusTypes.failed, message=str(einfo.exception))


detect_celery_task = DetectTask()
