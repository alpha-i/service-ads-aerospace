import logging
import os
import time

import pandas as pd
import numpy as np

from app import services
from app.interpreters.datasource.base import AbstractDatasourceInterpreter, InterpreterResult
from config import TEMPORARY_UPLOAD_FOLDER


class FlightDatasourceInterpreter(AbstractDatasourceInterpreter):

    MAX_SENSORS = 32
    
    def from_upload_to_dataframe(self, uploaded_file, datasource_type_id):

        flight = pd.DataFrame()
        errors = []
        base_file_name = os.path.basename(uploaded_file.filename)
        tmp_file = os.path.join(TEMPORARY_UPLOAD_FOLDER, f"{int(time.time())}_{base_file_name}")
        uploaded_file.save(tmp_file)

        try:
            with pd.HDFStore(tmp_file, 'r') as store:
                flights = list(store.keys())
                if len(flights) > 1:
                    errors.append(f"File must contain only one flight. Found {len(flights)}.")
                else:
                    flight = store.get(flights[0])
                    flight = flight.astype(np.float32)

            os.remove(tmp_file)
        except OSError as e:
            logging.debug(f"Trying to remove a non existent file {tmp_file}: {e}")
        except Exception as e:
            errors.append(str(e))

        if len(errors):
            return InterpreterResult(
                flight,
                errors
            )

        column_size = len(flight.columns)
        data_size = len(flight)

        datasource_config = services.datasource.get_configuration_by_id(datasource_type_id)

        if int(column_size) != int(datasource_config.meta['number_of_sensors']):
            errors.append("Wrong number of sensors {} found, {} expected".format(
                column_size,
                datasource_config.meta['number_of_sensors']
            ))

        if data_size < column_size:
            errors.append(f"Wrong data shape (data, sensors) ({data_size}, {column_size})")

        return InterpreterResult(
            flight,
            errors
        )


