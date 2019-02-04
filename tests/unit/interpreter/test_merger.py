import pytest

from app.core.utils import merge_dictionaries


@pytest.fixture(scope='module')
def starting_configuration():
    return {
        "datasource_class": "alphai_watson.datasource.flight.FlightDataSource",
        "datasource_interpreter": "FlightDatasourceInterpreter",
        "model": {
            "class_name": "alphai_rickandmorty_oracle.detective.RickAndMortyDetective",
            "configuration": {
                "model_configuration": {
                    "train_iters": 50000,
                    "number_of_timesteps": 2
                }
            }
        },
        "transformer": {
            "class_name": "alphai_watson.transformer.fft.FourierTransformer",
            "configuration": {
                "do_local_normalisation": False,
                "do_log_power": False,
                "number_of_sensors": 8,
                "number_of_timesteps": 392,
                "perform_pca": False
            }
        }
    }


def test_dictionary_merge(starting_configuration):
    train_configuration = {
        "model": {
          "configuration":{
              "model_configuration": {
                  "train_iters": 0
              }
          }
        },
        "transformer": {
            "configuration": {
                "perform_fft": False
            }
        }
    }

    merged_config = merge_dictionaries(starting_configuration, train_configuration)

    assert merged_config == {
        "datasource_class": "alphai_watson.datasource.flight.FlightDataSource",
        "datasource_interpreter": "FlightDatasourceInterpreter",
        "model": {
            "class_name": "alphai_rickandmorty_oracle.detective.RickAndMortyDetective",
            "configuration": {
                "model_configuration": {
                    "train_iters": 0,
                    "number_of_timesteps": 2
                }
            }
        },
        "transformer": {
            "class_name": "alphai_watson.transformer.fft.FourierTransformer",
            "configuration": {
                "do_local_normalisation": False,
                "do_log_power": False,
                "number_of_sensors": 8,
                "perform_fft": False,
                "number_of_timesteps": 392,
                "perform_pca": False
            }
        }
    }
