"""ML Prediction models - Storage for all 6 ML model outputs"""
from datetime import datetime
from app import db


class SiteRiskPrediction(db.Model):
    """Site Risk Classifier predictions (Random Forest model)"""
    __tablename__ = 'site_risk_predictions'

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False, index=True)
    prediction_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Prediction
    risk_level = db.Column(db.String(20), nullable=False)  # critical, high, medium, low
    risk_score = db.Column(db.Float)  # 0-100
    confidence = db.Column(db.Float)  # Model confidence

    # Risk probabilities
    prob_critical = db.Column(db.Float)
    prob_high = db.Column(db.Float)
    prob_medium = db.Column(db.Float)
    prob_low = db.Column(db.Float)

    # Feature importance for this prediction (top 5)
    top_features = db.Column(db.Text)  # JSON: {"feature": importance, ...}

    # Recommended actions
    recommended_frequency = db.Column(db.String(20))  # weekly, bi-weekly, monthly
    tests_per_year = db.Column(db.Integer)

    # Model info
    model_version = db.Column(db.String(50))
    model_accuracy = db.Column(db.Float)

    def __repr__(self):
        return f'<SiteRiskPrediction {self.site_id}: {self.risk_level}>'


class ContaminationPrediction(db.Model):
    """Contamination Classifier predictions (XGBoost model)"""
    __tablename__ = 'contamination_predictions'

    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.Integer, db.ForeignKey('water_samples.id'), index=True)
    analysis_id = db.Column(db.Integer, db.ForeignKey('analyses.id'))
    prediction_date = db.Column(db.DateTime, default=datetime.utcnow)

    # Prediction
    predicted_type = db.Column(db.String(50), nullable=False)
    confidence = db.Column(db.Float)

    # Class probabilities
    prob_runoff_sediment = db.Column(db.Float)
    prob_sewage_ingress = db.Column(db.Float)
    prob_salt_intrusion = db.Column(db.Float)
    prob_pipe_corrosion = db.Column(db.Float)
    prob_disinfectant_decay = db.Column(db.Float)

    # SHAP explanations (top contributing features)
    shap_explanations = db.Column(db.Text)  # JSON

    # Model info
    model_version = db.Column(db.String(50))
    f1_score = db.Column(db.Float)

    def __repr__(self):
        return f'<ContaminationPrediction {self.predicted_type}>'


class WaterQualityForecast(db.Model):
    """Water Quality Forecaster predictions (Gaussian Process model)"""
    __tablename__ = 'water_quality_forecasts'

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False, index=True)
    prediction_date = db.Column(db.DateTime, default=datetime.utcnow)
    forecast_date = db.Column(db.Date, nullable=False, index=True)  # Date being forecasted

    # Parameter being forecasted
    parameter = db.Column(db.String(50), nullable=False)  # ph, turbidity, tds, chlorine

    # Prediction with uncertainty
    predicted_value = db.Column(db.Float, nullable=False)
    lower_bound_95 = db.Column(db.Float)  # 95% CI lower
    upper_bound_95 = db.Column(db.Float)  # 95% CI upper
    uncertainty = db.Column(db.Float)  # Standard deviation

    # Threshold exceedance prediction
    prob_exceed_threshold = db.Column(db.Float)
    threshold_value = db.Column(db.Float)
    days_until_exceedance = db.Column(db.Integer)

    # Model info
    model_version = db.Column(db.String(50))
    r2_score = db.Column(db.Float)
    mae = db.Column(db.Float)

    def __repr__(self):
        return f'<WaterQualityForecast {self.site_id} {self.parameter}: {self.predicted_value}>'


class WQIReading(db.Model):
    """Real-time WQI readings (Penalty Scoring algorithm)"""
    __tablename__ = 'wqi_readings'

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False, index=True)
    sensor_id = db.Column(db.Integer, db.ForeignKey('iot_sensors.id'))
    reading_timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # WQI Score
    wqi_score = db.Column(db.Float, nullable=False)  # 0-100
    wqi_class = db.Column(db.String(20))  # Excellent, Compliant, Warning, Unsafe

    # Individual penalties
    ph_penalty = db.Column(db.Float, default=0)
    tds_penalty = db.Column(db.Float, default=0)
    turbidity_penalty = db.Column(db.Float, default=0)
    chlorine_penalty = db.Column(db.Float, default=0)
    temperature_penalty = db.Column(db.Float, default=0)
    coliform_penalty = db.Column(db.Float, default=0)

    # Raw values
    ph_value = db.Column(db.Float)
    tds_value = db.Column(db.Float)
    turbidity_value = db.Column(db.Float)
    chlorine_value = db.Column(db.Float)
    temperature_value = db.Column(db.Float)

    # Compliance
    is_drinkable = db.Column(db.Boolean)

    def __repr__(self):
        return f'<WQIReading {self.site_id}: {self.wqi_score} ({self.wqi_class})>'


class AnomalyDetection(db.Model):
    """Anomaly Detection results (Isolation Forest + CUSUM)"""
    __tablename__ = 'anomaly_detections'

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False, index=True)
    sensor_id = db.Column(db.Integer, db.ForeignKey('iot_sensors.id'))
    detection_timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Anomaly details
    is_anomaly = db.Column(db.Boolean, nullable=False)
    anomaly_type = db.Column(db.String(50))  # spike, drift, sudden_change, outlier
    anomaly_score = db.Column(db.Float)  # Isolation Forest score
    cusum_value = db.Column(db.Float)  # CUSUM statistic

    # Affected parameter
    parameter = db.Column(db.String(50))
    observed_value = db.Column(db.Float)
    expected_value = db.Column(db.Float)
    deviation_sigma = db.Column(db.Float)  # Number of standard deviations

    # Detection method
    detection_method = db.Column(db.String(50))  # isolation_forest, cusum, both
    model_version = db.Column(db.String(50))

    # Response
    alert_generated = db.Column(db.Boolean, default=False)
    alert_id = db.Column(db.Integer, db.ForeignKey('sensor_alerts.id'))
    acknowledged = db.Column(db.Boolean, default=False)
    acknowledged_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    acknowledged_at = db.Column(db.DateTime)

    def __repr__(self):
        return f'<AnomalyDetection {self.site_id}: {self.anomaly_type}>'


class DriftDetection(db.Model):
    """CUSUM Drift Detection results - Gradual parameter changes"""
    __tablename__ = 'drift_detections'

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False, index=True)
    sample_id = db.Column(db.Integer, db.ForeignKey('water_samples.id'), index=True)
    detection_timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    # Parameter being monitored
    parameter_name = db.Column(db.String(50), nullable=False)

    # Detection results
    drift_detected = db.Column(db.Boolean, default=False)
    drift_direction = db.Column(db.String(20))  # 'upward', 'downward', None
    drift_magnitude_sigma = db.Column(db.Float)  # How many std devs from baseline
    cusum_value = db.Column(db.Float)
    threshold = db.Column(db.Float, default=5.0)

    # Baseline statistics
    current_value = db.Column(db.Float)
    baseline_mean = db.Column(db.Float)
    baseline_std = db.Column(db.Float)

    # Model metadata
    model_version = db.Column(db.String(50), default='cusum_v1')

    def __repr__(self):
        return f'<DriftDetection {self.parameter_name}: {self.drift_direction if self.drift_detected else "stable"}>'


class CostOptimizationResult(db.Model):
    """Bayesian Cost Optimizer results"""
    __tablename__ = 'cost_optimization_results'

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), index=True)
    optimization_date = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    optimization_run_id = db.Column(db.String(50), index=True)  # Group results by run

    # Site classification
    risk_category = db.Column(db.String(20))  # critical, high, medium, low
    site_type = db.Column(db.String(50))

    # Optimization results
    current_tests_per_year = db.Column(db.Integer)
    optimized_tests_per_year = db.Column(db.Integer)
    current_cost_inr = db.Column(db.Float)
    optimized_cost_inr = db.Column(db.Float)
    cost_savings_inr = db.Column(db.Float)
    cost_reduction_percent = db.Column(db.Float)

    # Detection metrics
    detection_rate = db.Column(db.Float)  # % of contaminations detected
    false_negative_rate = db.Column(db.Float)
    coverage_score = db.Column(db.Float)

    # Recommendations
    recommended_frequency = db.Column(db.String(20))
    next_test_date = db.Column(db.Date)
    priority_rank = db.Column(db.Integer)

    # Model info
    model_version = db.Column(db.String(50))
    iteration = db.Column(db.Integer)

    def __repr__(self):
        return f'<CostOptimization {self.site_id}: {self.cost_reduction_percent}% savings>'


class ValidationResult(db.Model):
    """Pre-calculated validation metrics for ML models using 2-year train/test split"""
    __tablename__ = 'validation_results'

    id = db.Column(db.Integer, primary_key=True)
    site_id = db.Column(db.Integer, db.ForeignKey('sites.id'), nullable=False, index=True)

    # Training/Test split metadata
    training_start_date = db.Column(db.Date)
    training_end_date = db.Column(db.Date)
    test_start_date = db.Column(db.Date)
    test_end_date = db.Column(db.Date)
    training_samples_count = db.Column(db.Integer)
    test_samples_count = db.Column(db.Integer)

    # WQI Validation Metrics
    wqi_mae = db.Column(db.Float)  # Mean Absolute Error
    wqi_rmse = db.Column(db.Float)  # Root Mean Square Error
    wqi_accuracy_within_10 = db.Column(db.Float)  # % predictions within ±10 points
    wqi_predictions_count = db.Column(db.Integer)
    wqi_data_points = db.Column(db.JSON)  # Array of {date, predicted, actual, difference}

    # Contamination Type Validation Metrics
    contamination_accuracy = db.Column(db.Float)  # Overall accuracy %
    contamination_precision = db.Column(db.Float)
    contamination_recall = db.Column(db.Float)
    contamination_f1_score = db.Column(db.Float)
    contamination_predictions_count = db.Column(db.Integer)
    contamination_confusion_matrix = db.Column(db.JSON)  # {predicted_type: {actual_type: count}}

    # Risk Level Validation Metrics
    risk_accuracy = db.Column(db.Float)  # Overall accuracy %
    risk_predictions_count = db.Column(db.Integer)
    risk_confusion_matrix = db.Column(db.JSON)  # {predicted_level: {actual_level: count}}

    # Forecast Validation Metrics (per parameter)
    forecast_ph_r2 = db.Column(db.Float)
    forecast_ph_mae = db.Column(db.Float)
    forecast_ph_predictions_count = db.Column(db.Integer)

    forecast_turbidity_r2 = db.Column(db.Float)
    forecast_turbidity_mae = db.Column(db.Float)
    forecast_turbidity_predictions_count = db.Column(db.Integer)

    forecast_tds_r2 = db.Column(db.Float)
    forecast_tds_mae = db.Column(db.Float)
    forecast_tds_predictions_count = db.Column(db.Integer)

    forecast_temperature_r2 = db.Column(db.Float)
    forecast_temperature_mae = db.Column(db.Float)
    forecast_temperature_predictions_count = db.Column(db.Integer)

    # Overall forecast metrics
    forecast_avg_r2 = db.Column(db.Float)
    forecast_total_predictions = db.Column(db.Integer)

    # Calculation metadata
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    calculation_duration_seconds = db.Column(db.Float)  # How long it took to calculate
    is_valid = db.Column(db.Boolean, default=True)  # False if calculation failed
    error_message = db.Column(db.Text)  # Error details if calculation failed

    # Relationship
    site = db.relationship('Site', backref='validation_results')

    def __repr__(self):
        return f'<ValidationResult site_id={self.site_id} calculated={self.calculated_at}>'

    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'site_id': self.site_id,
            'training_period': {
                'start': self.training_start_date.isoformat() if self.training_start_date else None,
                'end': self.training_end_date.isoformat() if self.training_end_date else None,
                'samples': self.training_samples_count
            },
            'test_period': {
                'start': self.test_start_date.isoformat() if self.test_start_date else None,
                'end': self.test_end_date.isoformat() if self.test_end_date else None,
                'samples': self.test_samples_count
            },
            'wqi_metrics': {
                'mae': self.wqi_mae,
                'rmse': self.wqi_rmse,
                'accuracy_within_10': self.wqi_accuracy_within_10,
                'n_predictions': self.wqi_predictions_count,
                'data_points': self.wqi_data_points or []
            } if self.wqi_mae is not None else {},
            'contamination_metrics': {
                'accuracy': self.contamination_accuracy,
                'precision': self.contamination_precision,
                'recall': self.contamination_recall,
                'f1_score': self.contamination_f1_score,
                'n_predictions': self.contamination_predictions_count,
                'confusion_matrix': self.contamination_confusion_matrix or {}
            } if self.contamination_accuracy is not None else {},
            'risk_metrics': {
                'accuracy': self.risk_accuracy,
                'n_predictions': self.risk_predictions_count,
                'confusion_matrix': self.risk_confusion_matrix or {}
            } if self.risk_accuracy is not None else {},
            'forecast_metrics': {
                'ph': {'r2': self.forecast_ph_r2, 'mae': self.forecast_ph_mae, 'n_predictions': self.forecast_ph_predictions_count},
                'turbidity': {'r2': self.forecast_turbidity_r2, 'mae': self.forecast_turbidity_mae, 'n_predictions': self.forecast_turbidity_predictions_count},
                'tds': {'r2': self.forecast_tds_r2, 'mae': self.forecast_tds_mae, 'n_predictions': self.forecast_tds_predictions_count},
                'temperature': {'r2': self.forecast_temperature_r2, 'mae': self.forecast_temperature_mae, 'n_predictions': self.forecast_temperature_predictions_count},
                'avg_r2': self.forecast_avg_r2,
                'total_predictions': self.forecast_total_predictions
            } if self.forecast_avg_r2 is not None else {},
            'calculated_at': self.calculated_at.isoformat() if self.calculated_at else None,
            'calculation_duration_seconds': self.calculation_duration_seconds
        }
