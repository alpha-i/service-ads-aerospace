import logging
import math
import operator
from datetime import timedelta

import numpy as np

from app import services
from app.core.models import DiagnosticTask, DiagnosticResult
from app.entities import TaskStatusTypes
from app.entities.diagnostic import DiagnosticTaskEntity, DiagnosticTaskStatusEntity
from alphai_watson.detective import DiagnosticResult as DetectiveDiagnosticResult

from app.interpreters.dataview import DataView
from app.tasks.diagnose import diagnose_celery_task
from config import DEFAULT_VIEW_TIME_RESAMPLE_RULE


def get_task_by_code(detection_task_code):
    model = DiagnosticTaskEntity.get_for_detection_task_code(detection_task_code)
    return DiagnosticTask.from_model(model)


def get_all_for_company(company_id):
    models = DiagnosticTaskEntity.get_for_company(company_id)
    return DiagnosticTask.from_models(models)


def set_task_status(task_id, status, message=None):
    status = DiagnosticTaskStatusEntity(
        diagnostic_task_id=task_id,
        state=status.value,
        message=message
    )
    status.save()


def save_result(diagnostic_result):
    model = diagnostic_result.to_model()
    model.save()
    return DiagnosticResult.from_model(model)


def trigger_diagnostic(detection_task, upload_code):
    detection_task_code = detection_task.task_code

    diagnostic_task_entity = DiagnosticTaskEntity(
        detection_task_id=detection_task.id,
        task_code=detection_task_code,
        datasource_id=detection_task.datasource_id,
        company_id=detection_task.company_id,
        upload_code=upload_code
    )

    diagnostic_task_entity.save()
    status = DiagnosticTaskStatusEntity(
        diagnostic_task_id=diagnostic_task_entity.id,
        state=TaskStatusTypes.queued.value,
        message=f'Diagnostic for {detection_task_code} has been enqueued'
    )
    status.save()
    diagnose_celery_task.apply_async((upload_code, detection_task_code))

    return diagnostic_task_entity


def create_result_from_json(json_data):
    return DetectiveDiagnosticResult(
        chunk_index=json_data['chunk_index'],
        chunk_timedelta=json_data['chunk_timedelta'],
        synthetic_chunk=json_data['synthetic'],
        original_chunk=json_data['original']
    )


def calculate_most_anomalous_chunks(diagnostic_task, radius=1):
    detection_task = diagnostic_task._model.detection_task
    detection_result = services.detection.create_watson_detection_result_from_dictionary(
        detection_task.detection_result.result)

    k, x0, anomaly_prior = services.detection.load_calibration_values(detection_task)

    data_view = DataView.create_from_detection_result(detection_result, k, x0, anomaly_prior=anomaly_prior)

    original = data_view.to_dataframe()
    resampled = data_view.to_dataframe(DEFAULT_VIEW_TIME_RESAMPLE_RULE)

    anomalous_chunk_in_resampled = resampled.idxmax()[0]
    filter_start = anomalous_chunk_in_resampled - timedelta(seconds=1)
    filter_ends = anomalous_chunk_in_resampled + timedelta(seconds=1)

    anomalous_neighborhood = original.loc[filter_start:filter_ends]
    max_anomalous_value = anomalous_neighborhood.max().values[0]

    if k and x0 and anomaly_prior:
        probabilities = detection_result.get_probabilities(anomaly_prior=anomaly_prior, k=k, x0=x0)
    else:
        probabilities = detection_result.get_probabilities()

    most_anomalous_idx = [a for a in probabilities].index(max_anomalous_value)

    most_anomalous_idx = max(most_anomalous_idx, 1)

    start = most_anomalous_idx - radius
    end = most_anomalous_idx + radius
    list_of_chunk_indexes = list(range(start, end + 1))

    logging.info("Found chunks list [{}]".format(",".join(map(str, list_of_chunk_indexes))))

    return list_of_chunk_indexes


def group_adjacent_chunks(raw_diagnostic_result):
    group_list = []
    sorted_result = sorted(raw_diagnostic_result, key=lambda k: k['chunk_index'])

    adjacent_chunk_group = AdjacentChunkList()
    group_list.append(adjacent_chunk_group)

    for result in sorted_result:

        if not adjacent_chunk_group.can_be_added(result):
            adjacent_chunk_group = AdjacentChunkList()
            group_list.append(adjacent_chunk_group)

        adjacent_chunk_group.add_result(result)

    return group_list


class AdjacentChunkList:

    def __init__(self):
        self.list = []
        self.latest_index = None

    def can_be_added(self, result):

        if not self.latest_index:
            return True
        if result['chunk_index'] == (self.latest_index + 1):
            return True

        return False

    def add_result(self, result):
        self.list.append(result)
        self.latest_index = result['chunk_index']

    def get_cumulative_result(self):
        if len(self.list):
            first_element = self.list[0]

            chunk_index = first_element['chunk_index']
            chunk_timedelta = first_element['chunk_timedelta']

            original_shape = np.array(first_element['original']).shape
            cumulative_original = np.zeros((original_shape[0], original_shape[1] * len(self.list)))

            synthetic_shape = np.array(first_element['synthetic']).shape
            cumulative_synthetic = np.zeros((synthetic_shape[0], synthetic_shape[1] * len(self.list)))

            offset_x = 0
            for result in self.list:
                current_original = np.array(result['original'])

                offset_y = offset_x * current_original.shape[1]
                offset_z = offset_y + current_original.shape[1]
                cumulative_original[:, offset_y:offset_z] = current_original[:]

                current_synthetic = np.array(result['synthetic'])
                offset_y = offset_x * current_synthetic.shape[1]
                offset_z = offset_y + current_synthetic.shape[1]

                cumulative_synthetic[:, offset_y:offset_z] = current_synthetic[:]

                offset_x = offset_x + 1

            return DetectiveDiagnosticResult(
                chunk_index,
                chunk_timedelta,
                cumulative_synthetic,
                cumulative_original
            )


def calculate_frequency_index(data_size, chunk_length_in_seconds, downsample_factor):
    multiplier = downsample_factor / chunk_length_in_seconds
    return [
        round(multiplier * i, 2) for i in range(1, data_size + 1)
    ]
