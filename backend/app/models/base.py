# Import all models here so that Alembic can detect them automatically.
from app.core.database import Base
from app.models.user import User
from app.models.report import RoadReport
from app.models.image import ReportImage
from app.models.issue import Issue
from app.models.classification import ImageClassification
from app.models.assignment import IssueAssignment
from app.models.history import IssueStatusHistory




