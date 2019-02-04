import pandas as pd
import numpy as np

from flask import Blueprint, request, g, Response, jsonify

from app import services, ApiResponse
from app.core.auth import requires_access_token
from app.core.utils import handle_error
from app.interpreters.dataview import DataView
from app.services.transformer import SimpleTransformer, ResampleMethod
from config import DEFAULT_VIEW_TIME_RESAMPLE_RULE

diagnostic_blueprint = Blueprint('diagnostic', __name__)


@diagnostic_blueprint.route('/<detection_task_code>', methods=['GET'])
@requires_access_token
def detail(detection_task_code):
    diagnostic_task = services.diagnostic.get_task_by_code(detection_task_code)
    if not diagnostic_task:
        return handle_error(404, "No diagnostics found!")

    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        context={'diagnostic': diagnostic_task},
        template='diagnostic/detail.html',
    )

    return response()


@diagnostic_blueprint.route('/<string:detection_task_code>/result')
@requires_access_token
def result(detection_task_code):
    diagnostic_task = services.diagnostic.get_task_by_code(detection_task_code)
    if not diagnostic_task:
        return handle_error(404, "No diagnostics found!")

    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        context=diagnostic_task.diagnostic_result.result
    )

    return response()


@diagnostic_blueprint.route('/<detection_task_code>/plot', methods=['GET'])
@requires_access_token
def for_plot(detection_task_code):
    diagnostic_task = services.diagnostic.get_task_by_code(detection_task_code)
    if not diagnostic_task:
        return handle_error(404, "No diagnostics found!")

    detection_task = diagnostic_task._model.detection_task
    detection_result = services.detection.create_watson_detection_result_from_dictionary(detection_task.detection_result.result)
    chunk_duration_in_seconds = detection_result.get_chunk_duration() / 1000
    transformer_configuration = detection_task.training_task.configuration['transformer']['configuration']
    downsample_factor = transformer_configuration.get('downsample_factor', 4)

    diagnostic_result = diagnostic_task.diagnostic_result.result

    is_frequency_domain = diagnostic_task.is_frequency_domain
    data_keys = ['diagnostic', 'original', 'synthetic']

    for single_chunk in diagnostic_result:
        for key in data_keys:
            whole_signal_df = pd.DataFrame(single_chunk[key]).T
            if is_frequency_domain:
                positive_spectrum = _calculate_meaningful_fft_values(chunk_duration_in_seconds, whole_signal_df, downsample_factor)
                positive_spectrum = positive_spectrum.rename(
                    columns=lambda column: "Sensor {}".format(column)
                )

                single_chunk[key] = positive_spectrum.to_dict()
            else:
                data_frame = _build_chunk_data_for_time_plot(diagnostic_task, single_chunk['chunk_timedelta'], whole_signal_df)
                data_frame = data_frame.rename(
                    columns=lambda column: "Sensor {}".format(column)
                )

                single_chunk[key] = data_frame.to_dict()

    return jsonify({'diagnostic': diagnostic_task})


@diagnostic_blueprint.route('/<string:detection_task_code>/details/<int:chunk_index>/sensor/<int:sensor_id>')
@requires_access_token
def sensor_detail(detection_task_code, chunk_index, sensor_id):
    diagnostic_task = services.diagnostic.get_task_by_code(detection_task_code)
    if not diagnostic_task:
        return handle_error(404, "No diagnostics found!")

    training_task = diagnostic_task._model.detection_task.training_task
    transformer = services.watson.create_transformer_from_configuration(training_task)

    company = g.user.company

    datasource_class = services.watson.get_datasource_class_from_company_configuration(company.current_configuration)
    uploaded_file = services.datasource.get_by_upload_code(diagnostic_task.upload_code)

    datasource = datasource_class(uploaded_file.location, transformer)

    sensor_result = {}

    for resampling_method in [ResampleMethod.MEAN, ResampleMethod.MAX, ResampleMethod.MIN]:

        transformer = SimpleTransformer.create_from_original_transformer(transformer, resampling_method)
        datasource._transformer = transformer
        samples = list(datasource.get_test_data('NORMAL'))
        sample = samples[0]

        chunk = sample.get_chunk(chunk_index)
        chunk_timedelta = sample.get_timedelta_for_chunk(chunk_index)

        if len(chunk.shape) == 1:
            chunk = np.expand_dims(chunk, axis=0)

        sensor_result[resampling_method.value] = chunk[sensor_id]

    final_dataframe = _build_chunk_data_for_time_plot(
            diagnostic_task, chunk_timedelta, pd.DataFrame.from_dict(sensor_result))

    return Response(
        final_dataframe.to_csv(),
        mimetype='text/plain'
    )


def _build_chunk_data_for_time_plot(diagnostic_task, chunk_timedelta, data):
    detection_task = diagnostic_task._model.detection_task

    downsample_factor = detection_task.training_task.configuration['transformer']['configuration'].get('downsample_factor', 4)

    detection_result = services.detection.create_watson_detection_result_from_dictionary(detection_task.detection_result.result)

    data_view = DataView(data, detection_result.original_sample_rate//downsample_factor)
    data_frame = data_view.to_dataframe()
    data_frame.index = [str((index + pd.Timedelta(chunk_timedelta)).to_pytimedelta()) for index in
                        data_frame.index]
    data_frame.index.name = 'timedelta'
    return data_frame


def _build_chunk_data_for_frequency_plot(diagnostic_task, sensor_result):
    detection_task = diagnostic_task._model.detection_task
    detection_result = services.detection.create_watson_detection_result_from_dictionary(detection_task.detection_result.result)
    chunk_duration_in_seconds = detection_result.get_chunk_duration() / 1000

    return _calculate_meaningful_fft_values(chunk_duration_in_seconds, pd.DataFrame.from_dict(sensor_result))


def _calculate_meaningful_fft_values(chunk_duration_in_seconds, whole_signal_df, downsample_factor):
    data_length = whole_signal_df.shape[0]
    is_even = not (data_length % 2)
    low = 1
    if is_even:
        center = (data_length // 2)

        upper = center
    else:
        center = (data_length - 1) // 2
        upper = center + 1
    positive_spectrum = whole_signal_df[low:upper].copy()
    frequencies = services.diagnostic.calculate_frequency_index(positive_spectrum.shape[0], chunk_duration_in_seconds, downsample_factor)
    positive_spectrum['timedelta'] = frequencies
    positive_spectrum = positive_spectrum.set_index('timedelta')

    return positive_spectrum
