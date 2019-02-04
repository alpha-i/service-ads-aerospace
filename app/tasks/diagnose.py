import logging

import numpy  as np

import app.services.training
from app import services
from app.core.models import DiagnosticResult
from alphai_watson.detective import DiagnosticResult as DetectiveDiagnosticResult
from app.core.utils import json_reload
from app.entities import TaskStatusTypes
from app.tasks.base import BaseDBTask


def _ensure_dimension(data):

    if len(data.shape) == 1:
        data = data.reshape(1, data.shape[0])

    return data

class DiagnoseTask(BaseDBTask):
    name = 'diagnose_task'

    def run(self, upload_code, task_code, *args, **kwargs):
        uploaded_file = services.datasource.get_by_upload_code(upload_code)
        diagnostic_task = services.diagnostic.get_task_by_code(task_code)
        if not diagnostic_task or not uploaded_file:
            raise Exception("No task of upload file found!")

        services.diagnostic.set_task_status(
            task_id=diagnostic_task.id,
            status=TaskStatusTypes.started,
            message=f'Diagnostic for {task_code} has started!'
        )

        # ***** Start diagnostic

        detection_task_entity = diagnostic_task._model.detection_task

        training_task = app.services.training.get_training_for_id(detection_task_entity.training_task_id)

        training_task = app.services.training.update_root_folder_in_model_config(training_task)

        transformer = self._create_and_initialize_transformer(training_task)

        training_task = services.detective.set_correct_load_path_for_detection_and_diagnose(training_task)
        detective = services.detective.create_detective_from_configuration(training_task)

        company_id = uploaded_file.company_id
        company = services.company.get_by_id(company_id)

        datasource_class = services.watson.get_datasource_class_from_company_configuration(company.current_configuration)

        datasource = datasource_class(uploaded_file.location, transformer)

        samples = list(datasource.get_test_data('NORMAL'))
        sample = samples[0]

        chunk_list = services.diagnostic.calculate_most_anomalous_chunks(diagnostic_task)

        results = []
        for chunk_index in chunk_list:
            chunk = sample.get_chunk(chunk_index)
            chunk_timedelta = sample.get_timedelta_for_chunk(chunk_index)

            synthetic = detective.diagnose(chunk)
            synthetic = _ensure_dimension(synthetic)
            chunk = _ensure_dimension(chunk)
            diagnostic_result = DetectiveDiagnosticResult(
                chunk_index,
                chunk_timedelta,
                synthetic,
                chunk
            )

            results.append(diagnostic_result)

        # ***** End diagnostic

        services.diagnostic.save_result(
            DiagnosticResult(
                company_id=uploaded_file.company_id,
                diagnostic_task_id=diagnostic_task.id,
                upload_code=uploaded_file.upload_code,
                task_code=task_code,
                result=json_reload(results)
            )
        )

        services.diagnostic.set_task_status(
            task_id=diagnostic_task.id,
            status=TaskStatusTypes.successful,
            message=f'Diagnostic for {task_code} has completed successfully!'
        )

        logging.info(f"Task {task_code} for file {upload_code} ran successfully")
        return

    def _create_and_initialize_transformer(self, training_task):
        transformer = services.watson.create_transformer_from_configuration(training_task)
        training_datasource = app.services.training.create_training_datasource(training_task, transformer)
        # with this function we trigger the normalizer's viewing of the train data
        training_datasource.get_train_data('NORMAL')
        return training_datasource.transformer

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        task_code = args[1]
        logging.debug(f"Task {task_code} raised an exception: {einfo.exception!r}")
        detection_task = services.diagnostic.get_task_by_code(task_code)
        services.diagnostic.set_task_status(
            task_id=detection_task.id,
            status=TaskStatusTypes.failed,
            message=str(einfo.exception)
        )
        return


diagnose_celery_task = DiagnoseTask()

