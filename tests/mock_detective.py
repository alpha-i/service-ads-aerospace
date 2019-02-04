import numpy as np
from alphai_watson.datasource.flight import FlightDataSource
from alphai_watson.detective import DetectionResult
from alphai_watson.transformer import AbstractDataTransformer


class MockleRick:
    def train(self, sample):
        pass

    def detect(self, sample):
        sample_length = sample.data.shape[0]
        number_of_timesteps_in_chunk = 128
        original_sample_rate = 1024

        return DetectionResult(
            data=np.random.rand(sample_length // number_of_timesteps_in_chunk, ),
            n_timesteps_in_chunk=number_of_timesteps_in_chunk,
            original_sample_rate=original_sample_rate
        )


class MockTransformer(AbstractDataTransformer):
    def sample_processor(self, sample):
        return sample

    def process_stacked_samples(self, stacked_samples):
        return stacked_samples


class MockDataSource(FlightDataSource):
    pass
