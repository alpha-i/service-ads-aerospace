import abc

from collections import namedtuple

InterpreterResult = namedtuple('InterpreterResult', 'result errors')


class AbstractDatasourceInterpreter(metaclass=abc.ABCMeta):

    @abc.abstractmethod
    def from_upload_to_dataframe(self, uploaded_file, datasource_type_id):
        raise NotImplementedError
