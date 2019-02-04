from app.core.utils import import_class


def get_datasource_class_from_company_configuration(company_configuration):
    datasource_class_name = company_configuration.configuration['datasource_class']

    try:
        datasource_class = import_class(datasource_class_name)
    except ImportError:
        raise ImportError("No available datasource found for %s", datasource_class_name)

    return datasource_class


def create_transformer_from_configuration(entity_with_configuration):
    transformer_class = entity_with_configuration.configuration['transformer']['class_name']
    transformer_configuration = entity_with_configuration.configuration['transformer']['configuration']

    try:
        transformer = import_class(transformer_class)
    except ImportError:
        raise ImportError("No available transformer found for %s", transformer_class)

    return transformer(**transformer_configuration)
