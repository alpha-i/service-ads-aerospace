from flask import Blueprint, g, request

import app.services.training
from app import services, ApiResponse
from app.core.auth import requires_access_token

customer_blueprint = Blueprint('customer', __name__)


@customer_blueprint.route('/dashboard')
@requires_access_token
def dashboard():
    company = g.user.company
    detection_tasks = services.detection.get_tasks_by_company_id(g.user.company.id)
    datasource_configurations = services.datasource.get_configuration_by_company_id(g.user.company.id)
    training_task = app.services.training.get_tasks_by_company_id(g.user.company.id)

    latest_datasources = company.datasources[0:5]
    latest_detection_tasks = detection_tasks[0:5]
    latest_training_task = training_task[0:5]

    response = ApiResponse(
        content_type=request.accept_mimetypes.best,
        context={
            'datasources': latest_datasources,
            'detection_task_list': latest_detection_tasks,
            'datasource_configurations': datasource_configurations,
            'training_task_list': latest_training_task
        },
        template='dashboard.html'
    )

    return response()
