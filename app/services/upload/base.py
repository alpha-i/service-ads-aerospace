import logging
import os
from abc import ABCMeta, abstractmethod

from app import services

class UploadException(Exception):
    pass


class AbstractUploadManager(metaclass=ABCMeta):

    def __init__(self, company_configuration):
        self._company_configuration = company_configuration
        self._datasource_interpreter = services.company.get_datasource_interpreter(company_configuration)

    def _validate_extension(self, uploaded_file):
        root, extension = os.path.splitext(uploaded_file.filename)
        extension = extension.replace('.', '').lower()
        if extension not in self.allowed_extensions:
            raise UploadException(f"Invalid extension for upload {uploaded_file.filename}")

    def _validate_data_interpreter(self, uploaded_file, **kwargs):
        uploaded_dataframe, errors = self._datasource_interpreter.from_upload_to_dataframe(uploaded_file, **kwargs)

        if errors:
            raise UploadException(f"Invalid file uploaded: {'|'.join(errors)}")

        return uploaded_dataframe

    def validate(self, uploaded_file, **kwargs):
        self._validate_extension(uploaded_file)
        return self._validate_data_interpreter(uploaded_file, **kwargs)

    def cleanup(self, location):
        try:
            os.remove(location)
        except OSError as e:
            logging.warning(
                f"Trying to remove the original file {location} which doesn't exists while cleaning up"
            )

    def cleanup_temporary(self, upload_code):
        temporary_file = self._get_temp_filepath(upload_code)
        try:
            os.remove(temporary_file)
        except OSError as e:
            logging.warning(
                f"Trying to remove the temporary file {temporary_file} which doesn't exists while cleaning up"
            )

    @property
    @abstractmethod
    def has_confirmation_step(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def sample_rate(self):
        raise NotImplementedError

    @property
    @abstractmethod
    def allowed_extensions(self):
        raise NotImplementedError

    @abstractmethod
    def load_temporary(self, upload_code):
        raise NotImplementedError

    @abstractmethod
    def save_temporary(self, uploaded_dataframe, upload_code):
        raise NotImplementedError

    @abstractmethod
    def process(self, uploaded_dataframe, existing_dataframe=None):
        raise NotImplementedError

    @abstractmethod
    def store(self, uploaded_dataframe, upload_code):
        raise NotImplementedError

    @abstractmethod
    def _get_final_filepath(self, upload_code):
        raise NotImplementedError

    @abstractmethod
    def _get_temp_filepath(self, upload_code):
        raise NotImplementedError
