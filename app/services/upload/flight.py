import warnings

from pandas.errors import PerformanceWarning

warnings.simplefilter(action='ignore', category=PerformanceWarning)

import os

from app.services.upload.base import AbstractUploadManager
from config import UPLOAD_ROOT_FOLDER, HDF5_STORE_INDEX


class FlightUploadManager(AbstractUploadManager):

    @property
    def sample_rate(self):
        return 1024

    def _get_temp_filepath(self, upload_code):
        pass

    def cleanup_temporary(self, upload_code):
        pass

    def _get_final_filepath(self, upload_code):
        return os.path.join(UPLOAD_ROOT_FOLDER, upload_code + '.hdf5')

    @property
    def has_confirmation_step(self):
        return False

    def load_temporary(self, upload_code):
        pass

    def save_temporary(self, uploaded_dataframe, upload_code):
        pass

    @property
    def allowed_extensions(self):
        return ['hd5', 'h5', 'hdf5']

    def validate(self, uploaded_file, datasource_type_id):
        return super().validate(uploaded_file, datasource_type_id=datasource_type_id)

    def process(self, uploaded_dataframe, existing_dataframe=None):
        return uploaded_dataframe

    def store(self, final_dataframe, company_id, upload_code):
        upload_path = os.path.join(UPLOAD_ROOT_FOLDER, str(company_id))
        os.makedirs(upload_path, exist_ok=True)
        saved_path = os.path.join(upload_path, f'{upload_code}.hdf5')
        final_dataframe.to_hdf(saved_path, key=HDF5_STORE_INDEX)

        return saved_path
