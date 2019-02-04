import logging
import os
from copy import deepcopy

from alphai_watson.performance import GANPerformanceAnalysis
from sqlalchemy.orm.attributes import flag_modified

import app.services.training
from app import services
from app.entities import TrainingTaskEntity, TaskStatusTypes
from app.tasks.base import BaseDBTask
from config import TRAIN_ROOT_FOLDER


class ObjectWithConfiguration:

    def __init__(self, configuration):

        self.configuration = deepcopy(configuration)


class TrainTask(BaseDBTask):
    name = 'train_task'

    def run(self, training_task_code, *args, **kwargs):
        training_task_entity = TrainingTaskEntity.query.filter(
            TrainingTaskEntity.task_code==training_task_code).one_or_none()
        if not training_task_entity:
            logging.error(f"No training task found for {training_task_code}")
        app.services.training.set_task_status(training_task_entity, status=TaskStatusTypes.started, message='Started')

        mocked_training_task = ObjectWithConfiguration(training_task_entity.configuration)
        mocked_training_task = app.services.training.update_root_folder_in_model_config(mocked_training_task)

        detective = services.detective.create_detective_from_configuration(mocked_training_task)

        logging.info("Created detective")
        transformer = services.watson.create_transformer_from_configuration(mocked_training_task)
        datasource = app.services.training.create_training_datasource(training_task_entity, transformer)

        logging.info("Loaded datasource for training")

        logging.info("Start Training")
        is_a_retrain = training_task_entity.parent_training_id

        if not is_a_retrain:
            # this is not a retrain, so don't try to restore the model
            detective.model.load_path = None

        detective.train(datasource.get_train_data())

        if is_a_retrain:
            # if this is a retrain, load_path and save_path will be different
            # set the load to be the same as the previous save
            # to avoid loading an old checkpoint during calibration
            save_path = training_task_entity.configuration['model']['configuration']['model_configuration']['save_path']
            training_task_entity.configuration['model']['configuration']['model_configuration']['load_path'] = save_path
            detective.model.load_path = os.path.join(TRAIN_ROOT_FOLDER, save_path)

        performance = app.services.training.get_performance_analysis(mocked_training_task)

        k, x0, anomaly_prior = services.calibration.estimate_calibration_parameters(
            detective,
            datasource.get_test_data(),
            performance,
            datasource.get_train_data()
        )

        logging.info(
            f"Calibration parameter for {training_task_code}: k: {k}, x0: {x0}, anomaly_prior: {anomaly_prior}")

        calibration_parameters = {
            'k': k,
            'x0': x0,
            'anomaly_prior': anomaly_prior
        }

        training_task_entity.configuration['calibration'] = calibration_parameters
        flag_modified(training_task_entity, "configuration")
        training_task_entity.update()

        services.training.set_task_status(training_task_entity, status=TaskStatusTypes.successful, message='Successful')


    def on_failure(self, exc, task_id, args, kwargs, einfo):

        training_task_code = args[0]
        training_task_entity = TrainingTaskEntity.query.filter(TrainingTaskEntity.task_code==training_task_code).one_or_none()
        if not training_task_entity:
            logging.error(f'No training task code found for task {training_task_code}')
        logging.debug(f'Task {training_task_code} raised exception: {einfo.exception!r}\n{einfo.traceback!r}')
        app.services.training.set_task_status(training_task_entity, TaskStatusTypes.failed, message=str(einfo.exception))


train_celery_task = TrainTask()
