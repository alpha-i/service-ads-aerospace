import logging
import os

from alphai_watson.datasource import Sample
from alphai_watson.datasource.flight import FlightDataSource
from alphai_watson.performance import GANPerformanceAnalysis

from app.core.utils import merge_dictionaries
from app.entities import TrainingTaskStatusEntity, TrainingTaskEntity, TaskStatusTypes
from config import TRAIN_ROOT_FOLDER

DEFAULT_TRAIN_ITERS_ON_RETRAIN = 10000
DEFAULT_LEARN_RATE = 0.0001
DEFAULT_LEARN_RATE_ON_RETRAIN = DEFAULT_LEARN_RATE / 10


def set_task_status(training_task, status, message=None):
    training_task_status = TrainingTaskStatusEntity(
        training_task_id=training_task.id,
        state=status.value,
        message=message
    )
    training_task_status.save()
    return training_task_status


def get_tasks_by_company_id(company_id):
    return TrainingTaskEntity.query.filter(TrainingTaskEntity.company_id == company_id).order_by(
        TrainingTaskEntity.created_at.desc()
    ).all()


def filter_by_company_id(query, company_id):
    return query.filter(TrainingTaskEntity.company_id == company_id).order_by(TrainingTaskEntity.created_at.desc())


def filter_by_datasource_configuration_id(query, datasource_configuration_id):
    return query.filter(TrainingTaskEntity.datasource_configuration_id == datasource_configuration_id)


def filter_by_status(query, task_status_type ):
    return query.join(TrainingTaskStatusEntity).filter(TrainingTaskStatusEntity.state == task_status_type.value)


class TrainFlightDatasource(FlightDataSource):

    def __init__(self, sample_list, transformer):
        self._sample_list = sample_list
        self._transformer = transformer
        self._raw_data = self._read_samples()

    def _read_samples(self):
        flights = []
        for flight_dataframe in self._sample_list:
            flight_array = flight_dataframe.values
            logging.debug("Start reshape for flight")
            reshaped_flight_data = self._reshape_flight_data(flight_array)
            logging.debug("End reshape for flight")
            flights.append(reshaped_flight_data)

        return {'NORMAL': flights}

    @property
    def transformer(self):
        return self._transformer

    def get_train_data(self, *args, **kwargs):
        raw_samples = self._raw_data['NORMAL']
        data = self._extract_and_process_samples(raw_samples)
        total_length = data.shape[0]
        upper_limit = int(total_length * 0.8)
        return Sample(
            data=data[0:upper_limit],
            sample_type='NORMAL',
            sample_rate=self.sample_rate,
            number_of_timesteps=self._transformer.number_of_timesteps
        )

    def get_test_data(self, *args, **kwargs):
        raw_samples = self._raw_data['NORMAL']
        data = self._extract_and_process_samples(raw_samples)
        total_length = data.shape[0]
        upper_limit = int(total_length * 0.8)

        return Sample(
            data=data[upper_limit:],
            sample_type='NORMAL',
            sample_rate=self.sample_rate,
            number_of_timesteps=self._transformer.number_of_timesteps
        )


def create_training_datasource(training_task, transformer):
    sample_list = []
    for datasource in training_task.datasources:
        sample_list.append(
            datasource.get_file()
        )

    return TrainFlightDatasource(
        sample_list,
        transformer
    )


def create_training_configuration(training_task_code,
                                  company_id,
                                  company_configuration,
                                  datasource_configuration_meta,
                                  enable_fft=None,
                                  parent_training_id=None
                                  ):
    logging.info(f"Create training configuration for task code {training_task_code}")

    save_train_path = os.path.join(str(company_id), training_task_code, training_task_code)
    load_train_path = save_train_path
    train_iters = company_configuration['model']['configuration']['model_configuration']['train_iters']
    learning_rate = DEFAULT_LEARN_RATE
    if parent_training_id:
        parent_task = get_training_for_id(parent_training_id)
        if parent_task:
            logging.info("The Training has parent task. Updating loading_path")
            load_train_path = parent_task.training_save_path
            enable_fft = parent_task.has_fft_enabled
            # train_iters = DEFAULT_TRAIN_ITERS_ON_RETRAIN
            learning_rate = DEFAULT_LEARN_RATE_ON_RETRAIN

    modified_training_configuration = {
        'model': {
            'configuration': {
                'model_configuration': {
                    'load_path': load_train_path,
                    'save_path': save_train_path,
                    'train_iters': train_iters,
                    'learning_rate': learning_rate
                }
            }
        },
        'transformer': {
            'configuration': {
                'enable_fft': enable_fft,
                'number_of_sensors': datasource_configuration_meta['number_of_sensors'],
                'number_of_timesteps': datasource_configuration_meta['number_of_timesteps'],
                'downsample_factor': datasource_configuration_meta.get('downsample_factor', 4)
                # 4 is the default parameter, deep down the transformaer in watson
            }
        }
    }

    training_configuration = merge_dictionaries(company_configuration, modified_training_configuration)

    return training_configuration


def update_root_folder_in_model_config(training_task_entity):

    load_relative_path = training_task_entity.configuration['model']['configuration']['model_configuration'][
        'load_path']

    load_full_path = os.path.join(TRAIN_ROOT_FOLDER, load_relative_path)

    training_task_entity.configuration['model']['configuration']['model_configuration']['load_path'] = load_full_path

    save_relative_path = training_task_entity.configuration['model']['configuration']['model_configuration'][
        'save_path']
    save_full_path = os.path.join(TRAIN_ROOT_FOLDER, save_relative_path)
    training_task_entity.configuration['model']['configuration']['model_configuration']['save_path'] = save_full_path

    return training_task_entity


def get_training_for_task_code(training_task_code):
    return TrainingTaskEntity.get_for_task_code(training_task_code)


def get_training_for_id(training_task_id):
    return TrainingTaskEntity.query.filter(TrainingTaskEntity.id == training_task_id).one_or_none()


def get_available_training_for_datasource(datasource):
    training_tasks = TrainingTaskEntity.query.filter(TrainingTaskEntity.datasource_configuration_id==datasource.datasource_configuration_id).all()
    return [training_task for training_task in training_tasks if training_task.status == TaskStatusTypes.successful.value]


def delete(training_task):
    model = training_task._model
    model.delete()


def get_performance_analysis(training_task_entity):
    return GANPerformanceAnalysis({})
