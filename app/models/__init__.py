"""
Jal Sarovar - Database Models
"""
from app.models.user import User
from app.models.water_sample import WaterSample
from app.models.test_result import TestResult
from app.models.analysis import Analysis
from app.models.site import Site
from app.models.water_level import WaterLevel, WaterLevelTrend
from app.models.visual_observation import VisualObservation, VisualTrendAnalysis
from app.models.robot_measurement import RobotMeasurement, RobotFleet
from app.models.residential_site import (
    ResidentialSite,
    ResidentialMeasurement,
    ResidentialAlert,
    ResidentialSubscription
)
from app.models.notification_log import NotificationLog
from app.models.wqi_calculation import WQICalculation

__all__ = [
    # Core Models (Public Water Monitoring)
    'User',
    'WaterSample',
    'TestResult',
    'Analysis',
    'Site',
    'WaterLevel',
    'WaterLevelTrend',
    'VisualObservation',
    'VisualTrendAnalysis',
    'RobotMeasurement',
    'RobotFleet',

    # Residential Models (Home/Apartment Monitoring)
    'ResidentialSite',
    'ResidentialMeasurement',
    'ResidentialAlert',
    'ResidentialSubscription',

    # Communication & Notifications
    'NotificationLog',

    # ML & Analytics
    'WQICalculation',
]
