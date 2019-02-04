import enum
import numpy as np
from alphai_watson.transformer import AbstractDataTransformer

D_TYPE = np.float32


class ResampleMethod(enum.Enum):
    MEAN = 'mean'
    MAX = 'max'
    MIN = 'min'


class SimpleTransformer(AbstractDataTransformer):

    def __init__(self, number_of_timesteps, number_of_sensors, downsample_factor=4, resample_method=ResampleMethod.MEAN):
        super().__init__(number_of_timesteps, number_of_sensors)
        self._sample_length = number_of_timesteps
        self.normalisation = None
        self.downsample_factor = downsample_factor
        self._resample_method = resample_method

    def reshape(self, data):
        return data

    def _trim_sample(self, sample):
        """ Removes end of segment to ensure integer multiples of feature_length is available. """

        len_segment = sample.shape[1]

        n_total_chunks = len_segment // self._sample_length
        max_index = n_total_chunks * self._sample_length

        return sample[:, 0:max_index]

    def sample_processor(self, sample, normalise_each_sample=False):
        """ For each flight we shall normalise each sensors overall signal to zero mean and unity rms. """

        return sample.astype(D_TYPE)

    def process_stacked_samples(self, full_data):
        """  Prepare list of large data samples for entry into network.
        :param full_data: array of [n_sensors, n_timesteps]
        :return: 4D nparray of shape [n_chunks, feature_length, n_sensors]
        """

        full_data = full_data.astype(np.float32, copy=False)

        n_sensors = full_data.shape[0]
        full_data = np.swapaxes(full_data, 0, 1)  # [n_all_timesteps, n_sensors]
        full_data = np.reshape(full_data, (-1, self._sample_length, n_sensors))  # [n_chunks, n_timesteps, n_sensors]
        full_data = full_data.swapaxes(1, 2)  # [n_chunks, n_sensors, n_timesteps]

        if self.downsample_factor > 1:
            data_shape = full_data.shape
            denominator = data_shape[2] // self.downsample_factor
            new_shape = (data_shape[0], data_shape[1], denominator, self.downsample_factor)

            temp = full_data.reshape(new_shape)

            if self._resample_method == ResampleMethod.MEAN:
                full_data = np.mean(temp, axis=-1, dtype=D_TYPE)
            elif self._resample_method == ResampleMethod.MAX:
                full_data = np.max(temp, axis=-1)
            elif self._resample_method == ResampleMethod.MIN:
                full_data = np.min(temp, axis=-1)

        return full_data  # [n_chunks, feature_length, n_sensors]

    @staticmethod
    def create_from_original_transformer(original_transformer, resample_method):

        return SimpleTransformer(
            original_transformer.number_of_timesteps,
            original_transformer.number_of_sensors,
            original_transformer.downsample_factor,
            resample_method
        )
