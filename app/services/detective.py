import logging

from app.core.utils import import_class


def create_detective_from_configuration(entity_with_configuration):
    detective_class = entity_with_configuration.configuration['model']['class_name']
    detective_configuration = entity_with_configuration.configuration['model']['configuration']

    try:
        detective = import_class(detective_class)
    except ImportError:
        raise ImportError("No available detective found for %s", detective_class)

    return detective(**detective_configuration)


def train(oracle, detection_request, data_dict):
    start_time = detection_request['start_time']
    logging.debug(f"Start training {oracle}, start time {start_time}")
    oracle.train(data_dict, start_time)
    logging.debug(f"Training for {oracle} is done!")


def predict(oracle, detection_request, data_dict):
    start_time = detection_request['start_time']
    logging.debug(f"Start detection with {oracle}, start time {start_time}")
    oracle_detection_result = oracle.predict(
        data=data_dict,
        current_timestamp=start_time
    )
    logging.debug(f"{oracle} successfully returned a detection!")
    return oracle_detection_result


def set_correct_load_path_for_detection_and_diagnose(entity_with_configuration):

    logging.info("Setting correct load path for detection/diagnose")
    save_path = entity_with_configuration.configuration['model']['configuration']['model_configuration']['save_path']
    entity_with_configuration.configuration['model']['configuration']['model_configuration']['load_path'] = save_path

    logging.info(f"new load_path {save_path}")

    return entity_with_configuration
