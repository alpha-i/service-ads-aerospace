import pandas as pd
import numpy as np
from alphai_watson.detective import DetectionResult


class DataView:

    def __init__(self, data_frame, sample_rate):
        self._sample_rate = sample_rate
        self._data_frame = self._add_timedelta_index(data_frame)

    @property
    def dataframe(self):
        return self._data_frame

    @property
    def sample_rate(self):
        return self._sample_rate

    def _add_timedelta_index(self, data_frame):
        data_length = data_frame.shape[0]
        duration_in_milliseconds = 1000 / self._sample_rate
        data_frame['timedelta'] = pd.TimedeltaIndex(
            periods=data_length, start=0, freq=f"{round(duration_in_milliseconds, 6)}L"
        )
        return data_frame.set_index('timedelta')

    def wrap_columns_name(self, format_string):
        """
        Rename the source column according to a format string

        :param str format_string: a string with {} placeholder
        """
        self._data_frame = self._data_frame.rename(
            columns=lambda column: format_string.format(column)
        )

    def to_dataframe(self, resample_rule=None, normalize=False):
        if resample_rule:
            data_frame = self._data_frame.resample(resample_rule).mean()
            data_frame.fillna(method='ffill', inplace=True)
        else:
            data_frame = self._data_frame

        if normalize:
            data_frame = (data_frame - data_frame.mean()) / (data_frame.max() - data_frame.min())

        return data_frame

    def to_csv(self, resample_rule=None, normalize=False):
        return self.to_dataframe(resample_rule, normalize).to_csv()

    def to_dict(self, resample_rule=None, normalize=False):
        data_frame = self.to_dataframe(resample_rule, normalize)

        datasets = []
        labels = [str(delta.to_pytimedelta()) for delta in data_frame.index]

        for label, data in data_frame.to_dict().items():
            datasets.append(
                {
                    'label': label,
                    'data': [value for _, value in data.items()]
                }
            )

        return {
            'labels': labels,
            'datasets': datasets
        }

    def __add__(self, other_data_view):

        if other_data_view.sample_rate != self._sample_rate:
            raise ValueError("Sample rate mismatch between dataframes: {}/{}".format(
                self._sample_rate,
                other_data_view.sample_rate
            ))

        return DataView(
            pd.concat([self._data_frame, other_data_view.dataframe], axis=1),
            self.sample_rate
        )

    @staticmethod
    def create_from_detection_result(detection_result, k=None, x0=None, anomaly_prior=None):

        if k and x0 and anomaly_prior:
            probabilities = detection_result.get_probabilities(anomaly_prior=anomaly_prior, k=k, x0=x0)
        else:
            probabilities = detection_result.get_probabilities()
        return DataView(
            pd.DataFrame(probabilities),
            detection_result.sample_rate
        )

    @staticmethod
    def create_from_datasource(datasource):
        return DataView(
            datasource.get_file(),
            int(datasource.meta['sample_rate'])
        )
