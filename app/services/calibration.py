# After training a model, we need to establish calibration based on its predictive accuracy
import logging
from copy import deepcopy
from pprint import pformat

import numpy as np
from alphai_watson.performance import AnomalyTypes, ResultCollector
from scipy.optimize import minimize

ANOMALY_PRIOR_PERCENTILE = 99

DEFAULT_ANOMALY_PRIOR = 0.5

MAX_POSTERIOR_PROBABILITY_TRAIN = 0.2

ANOMALY_CONTAMINATION_AMPLITUDES = [0.01, 0.1, 0.5, 1, 2]
ANOMALY_TIME_SHIFT = [0.01, 0.1, 0.25, 0.5]
ANOMALY_MULTIPLICATIVE_FACTOR = [1.01, 1.1, 1.5, 2]

N_CHUNK_INDEX = 0
N_SENSORS_INDEX = 1
N_TIMESTEPS_CHUNK_INDEX = 2


def calculate_anomaly_prior(default_posterior, posterior_probability):
    likelihood_ratio = 1 / default_posterior - 1
    anomaly_prior = posterior_probability * likelihood_ratio / (1 + posterior_probability * (likelihood_ratio - 1))

    return float(anomaly_prior)


def estimate_calibrated_probabilities(k, x0, raw_outputs):
    """ Determine probability of anomaly p(D|a) given a set of calibration parameters. """
    return 1 / (1 + np.exp(-k * (raw_outputs - x0)))


def estimate_calibration_parameters(detective, test_data, performance, train_data):
    """ First runs a sequence of tests of the model, before finding the best-fit calibration parameters

    :param AbstractDetective detective: AbstractDetective
    :param Sample test_data:
    :param PerformanceAnalysis performance:

    :return: float, float the best-fit calibration parameters
    """

    logging.info("Starting calibration")

    logging.info("Detecting test data")
    normal_detection_result = detective.detect(test_data)

    normal_true_value = AnomalyTypes[test_data.type].value

    abnormal_flights = _build_list_of_abnormal_flights(test_data)

    raw_perfomance_array = np.zeros(len(abnormal_flights))
    raw_outputs = np.zeros(len(abnormal_flights))

    # Establish performance accuracy
    for i, abnormal_sample in enumerate(abnormal_flights):
        logging.info(f"Analysing fake abnormal flight {i} data")

        abnormal_detection_result = detective.detect(abnormal_sample)
        raw_outputs[i] = np.median(abnormal_detection_result.data)

        abnormal_true_value = AnomalyTypes[abnormal_sample.type].value

        result_collector = ResultCollector()
        result_collector.add_result(0, abnormal_detection_result, abnormal_true_value)
        result_collector.add_result(1, normal_detection_result, normal_true_value)

        logging.info(f"Detecting score for fake abnormal flight {i} data")

        chunk_roc_score = performance.analyse(result_collector.chunk_score, result_collector.chunk_true_value)
        logging.info(f"RAW ROC score for flight {i} was:")
        logging.info(pformat(chunk_roc_score))
        raw_perfomance_array[i] = np.abs(chunk_roc_score - 0.5) + 0.5  # Deviation from 0.5 corresponds to enhanced performance

    logging.info(f"RAW Performance array for calibration:")
    logging.info(pformat(raw_perfomance_array))
    logging.info(f"Raw outputs for calibration:")
    logging.info(pformat(raw_outputs))

    # With these stats we now compute the maximum likelihood calibration parameters

    initial_guess = [1.0, 0.0]
    minimisation_result = minimize(_calibration_cost, initial_guess,
                                   args=(raw_outputs, raw_perfomance_array))

    k = minimisation_result.x[0]
    x0 = minimisation_result.x[1]

    # calibrate anomaly prior

    default_posterior_probabilities = normal_detection_result.get_probabilities(
        anomaly_prior=DEFAULT_ANOMALY_PRIOR,
        x0=x0, k=k)

    max_default_posterior = np.min([np.percentile(default_posterior_probabilities, ANOMALY_PRIOR_PERCENTILE), 0.99])

    anomaly_prior = calculate_anomaly_prior(max_default_posterior, MAX_POSTERIOR_PROBABILITY_TRAIN)

    return k, x0, anomaly_prior


def _build_list_of_abnormal_flights(test_data):
    total_samples = []

    # apply contamination amplitudes
    for i in range(len(ANOMALY_CONTAMINATION_AMPLITUDES)):
        amplitude = ANOMALY_CONTAMINATION_AMPLITUDES[i]
        new_test_data = deepcopy(test_data)
        new_test_data.data = _add_amplitude_contamination(test_data.data, amplitude)
        new_test_data.type = 'ABNORMAL'
        total_samples.append(new_test_data)

    # apply time_shift anomaly
    for i in range(len(ANOMALY_TIME_SHIFT)):
        time_shift = ANOMALY_TIME_SHIFT[i]
        new_test_data = deepcopy(test_data)
        new_test_data.data = _add_timeshift_contamination(test_data.data, time_shift)
        new_test_data.type = 'ABNORMAL'
        total_samples.append(new_test_data)

    # apply multiplicative anomaly
    for i in range(len(ANOMALY_MULTIPLICATIVE_FACTOR)):
        multiplicative_factor = ANOMALY_MULTIPLICATIVE_FACTOR[i]
        new_test_data = deepcopy(test_data)
        new_test_data.data = _add_multiplicative_contamination(test_data.data, multiplicative_factor)
        new_test_data.type = 'ABNORMAL'
        total_samples.append(new_test_data)

    return total_samples


def _add_amplitude_contamination(original_flight, abnormality_fraction):
    contamination = np.roll(original_flight, shift=1, axis=N_SENSORS_INDEX)

    return (original_flight + abnormality_fraction * contamination) / (1.0 + abnormality_fraction)


def _add_timeshift_contamination(original_flight, timeshift_percentage):
    places_to_shift = int(original_flight.shape[1] * timeshift_percentage)
    contamination = np.roll(original_flight, shift=places_to_shift, axis=1)

    return (original_flight + contamination) / 2


def _add_multiplicative_contamination(original_flight, multiplication_factor):
    return original_flight * multiplication_factor


def _calibration_cost(constants, raw_outputs, performance_array):
    """  Wish to minimise this function when seeking optimal values of k and x0.

    :param constants: Array of parameters to be optimised
    :param raw_outputs: Network outputs
    :param performance_array: Actual network performance
    :return: A measure of how well the constants do at describing the probabilities.
    """

    k = constants[0]
    x0 = constants[1]
    estimated_performance = estimate_calibrated_probabilities(k, x0, raw_outputs)
    cost = np.abs(estimated_performance - performance_array)

    return np.sum(cost)
