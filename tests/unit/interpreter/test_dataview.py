import os
import pickle

import numpy as np
import pandas as pd
from alphai_watson.datasource import AbstractDataSource
from alphai_watson.detective import DetectionResult

from app.interpreters.dataview import DataView
from tests import RESOURCE_DIR


class DummyDataSource:

    def __init__(self, location, sample_rate, store_index):
        """

        :param str location:
        :param int sample_rate:
        :param str store_index:
        """

        self.location = location
        self.sample_rate = sample_rate
        self.store_index = store_index

    def get_file(self):
        with pd.HDFStore(self.location) as hdf_store:
            dataframe = hdf_store[self.store_index]
            return dataframe

    @property
    def meta(self):
        return {
            'sample_rate': self.sample_rate
        }


class DummyDetectionResult(DetectionResult):

    def __init__(self, data, timesteps_per_chunk, original_sample_rate):
        super().__init__(data, timesteps_per_chunk, original_sample_rate)
        self._data = data
        self.timesteps_per_chunk = timesteps_per_chunk
        self._original_sample_rate = original_sample_rate


def test_create_from_detection_result():
    data_view = DataView.create_from_detection_result(
        DummyDetectionResult(
            np.zeros(1000),
            10,
            100
        )
    )

    assert isinstance(data_view, DataView)

    dataframe = data_view.dataframe
    assert isinstance(dataframe, pd.DataFrame)
    assert isinstance(dataframe.index, pd.TimedeltaIndex)


def test_create_from_datasource():
    data_source = DummyDataSource(
        os.path.join(RESOURCE_DIR, 'test_good_file_fight.hd5'),
        1024,
        'df1'
    )

    data_view = DataView.create_from_datasource(data_source)

    assert isinstance(data_view, DataView)

    dataframe = data_view.dataframe
    assert isinstance(dataframe, pd.DataFrame)
    assert isinstance(dataframe.index, pd.TimedeltaIndex)


def test_data_view_index():
    sample_rate = 1024

    data_view = DataView(
        pd.DataFrame(np.random.rand(sample_rate * 4)),
        sample_rate
    )

    dataframe = data_view.dataframe

    assert dataframe.index[0] == pd.Timedelta(milliseconds=0)

    one_sample_duration_in_ms = 1000 / 1024
    last_data_index = (dataframe.shape[0] - 1)

    last_dataframe_index = dataframe.index[-1]

    expected_index = pd.Timedelta(milliseconds=(round(one_sample_duration_in_ms, 6) * last_data_index))

    assert last_dataframe_index.to_pytimedelta() == expected_index.to_pytimedelta()


def test_data_view_rename_columns():
    sample_rate = 1024

    data_view = DataView(
        pd.DataFrame(np.random.rand(sample_rate * 4)),
        sample_rate
    )

    data_view.wrap_columns_name("Sensor {}")
    assert data_view.dataframe.columns == ['Sensor 0']

    data_view.wrap_columns_name("Gesu")
    assert data_view.dataframe.columns == ['Gesu']


def test_data_view_to_dict():
    sample_rate = 1

    data_view = DataView(
        pd.DataFrame(np.random.rand(sample_rate * 3)),
        sample_rate
    )

    data_view.wrap_columns_name('Sensor {}')
    data_dict = data_view.to_dict()

    assert data_dict['labels'] == ['0:00:00', '0:00:01', '0:00:02']
    assert len(data_dict['datasets']) == 1
    assert data_dict['datasets'][0]['label'] == 'Sensor 0'


def test_data_view_merge():
    sample_rate = 1

    datasource_view = DataView(
        pd.DataFrame(np.random.rand(sample_rate * 3)),
        sample_rate
    )

    datasource_view.wrap_columns_name('Sensor {}')

    detection_result_view = DataView(
        pd.DataFrame(np.random.rand(sample_rate * 3)),
        sample_rate
    )

    detection_result_view.wrap_columns_name('Result {}')

    merged = datasource_view + detection_result_view

    assert list(merged.dataframe.columns) == ['Sensor 0', 'Result 0']
