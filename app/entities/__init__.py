from app.entities.base import BaseEntity, TaskStatusTypes
from app.entities.customer import (
    UserEntity, CompanyEntity, CompanyConfigurationEntity,
    CustomerActionEntity, UserProfileEntity, Actions
)
from app.entities.datasource import DataSourceEntity
from app.entities.detection import (
    DetectionTaskEntity, DetectionTaskStatusEntity, DetectionResultEntity
)

from app.entities.diagnostic import (
    DiagnosticTaskEntity, DiagnosticTaskStatusEntity, DiagnosticResultEntity
)

from app.entities.training import (
    TrainingTaskEntity, TrainingTaskStatusEntity
)
