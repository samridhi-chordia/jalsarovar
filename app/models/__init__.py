"""
Jal Sarovar Database Models
All SQLAlchemy ORM models for the water quality management system
"""
from app.models.user import User
from app.models.role_permission import RolePermission
from app.models.site import Site
from app.models.water_sample import WaterSample
from app.models.test_result import TestResult
from app.models.analysis import Analysis
from app.models.intervention import Intervention, TreatmentMethod
from app.models.ml_prediction import (
    SiteRiskPrediction, ContaminationPrediction,
    WaterQualityForecast, AnomalyDetection, WQIReading,
    CostOptimizationResult, DriftDetection, ValidationResult
)
from app.models.iot_sensor import IoTSensor, SensorReading, SensorAlert
from app.models.system_config import SystemConfig, CONFIGURABLE_SETTINGS, CONFIG_CATEGORIES
from app.models.visual_observation import VisualObservation
from app.models.data_import import DataSource, ImportBatch
from app.models.visitor import VisitorStats, Visit

__all__ = [
    'User', 'RolePermission', 'Site', 'WaterSample', 'TestResult', 'Analysis',
    'Intervention', 'TreatmentMethod',
    'SiteRiskPrediction', 'ContaminationPrediction',
    'WaterQualityForecast', 'AnomalyDetection', 'WQIReading',
    'CostOptimizationResult', 'DriftDetection', 'ValidationResult',
    'IoTSensor', 'SensorReading', 'SensorAlert',
    'SystemConfig', 'CONFIGURABLE_SETTINGS', 'CONFIG_CATEGORIES',
    'DataSource', 'ImportBatch',
    'VisitorStats', 'Visit'
]
