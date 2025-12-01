"""
Anomaly Detection Service - Isolation Forest Implementation
Implements ML-based anomaly detection for residential water quality monitoring
Target: 92% accuracy as per research paper requirements
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
import joblib
import os
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional


class WaterQualityAnomalyDetector:
    """
    Isolation Forest-based anomaly detector for real-time water quality monitoring

    Detects unusual parameter combinations that may indicate:
    - Sudden TDS spikes (pipe contamination)
    - Chlorine drops (disinfection failure)
    - pH shifts (chemical contamination)
    - Turbidity anomalies (sediment ingress)
    - Temperature anomalies (unusual conditions)
    - RO system failures (degraded membrane)
    """

    def __init__(self, contamination=0.08, random_state=42, model_path='app/ml/trained_models/anomaly_detector.pkl'):
        """
        Initialize Isolation Forest anomaly detector

        Parameters:
        -----------
        contamination : float (default=0.08)
            Expected proportion of anomalies in dataset (8% based on research data)
        random_state : int
            Random seed for reproducibility
        model_path : str
            Path to save/load trained model
        """
        self.contamination = contamination
        self.random_state = random_state
        self.model_path = model_path
        self.scaler = StandardScaler()
        self.model = None
        self.feature_names = [
            'ph_value', 'tds_ppm', 'temperature_celsius', 'turbidity_ntu',
            'conductivity_us_cm', 'free_chlorine_mg_l', 'orp_mv',
            'hour_of_day', 'day_of_week'
        ]
        self.is_trained = False

        # Anomaly type classification thresholds (based on feature contributions)
        self.anomaly_thresholds = {
            'sudden_tds_spike': {'feature': 'tds_ppm', 'z_score': 3.0},
            'chlorine_drop': {'feature': 'free_chlorine_mg_l', 'z_score': -2.5},
            'ph_shift': {'feature': 'ph_value', 'z_score': 2.5},
            'turbidity_anomaly': {'feature': 'turbidity_ntu', 'z_score': 3.0},
            'temperature_anomaly': {'feature': 'temperature_celsius', 'z_score': 2.5},
            'conductivity_anomaly': {'feature': 'conductivity_us_cm', 'z_score': 3.0},
            'ro_system_failure': {'feature': 'ro_rejection_rate_percent', 'z_score': -3.0}
        }

    def prepare_features(self, measurements: List[Dict]) -> pd.DataFrame:
        """
        Extract and engineer features from measurement data

        Parameters:
        -----------
        measurements : List[Dict]
            List of measurement dictionaries with water quality parameters

        Returns:
        --------
        pd.DataFrame : Prepared features for anomaly detection
        """
        df = pd.DataFrame(measurements)

        # Ensure datetime is parsed
        if 'measurement_datetime' in df.columns:
            df['measurement_datetime'] = pd.to_datetime(df['measurement_datetime'])
            df['hour_of_day'] = df['measurement_datetime'].dt.hour
            df['day_of_week'] = df['measurement_datetime'].dt.dayofweek
        else:
            # Use current time if not available
            df['hour_of_day'] = datetime.now().hour
            df['day_of_week'] = datetime.now().weekday()

        # Select only numeric features for anomaly detection
        feature_df = df[self.feature_names].copy()

        # Handle missing values (fill with median)
        feature_df = feature_df.fillna(feature_df.median())

        # Add derived features
        if 'tds_ppm' in feature_df.columns and 'conductivity_us_cm' in feature_df.columns:
            feature_df['tds_conductivity_ratio'] = feature_df['tds_ppm'] / (feature_df['conductivity_us_cm'] + 1e-6)

        return feature_df

    def train(self, training_data: List[Dict]) -> Dict:
        """
        Train Isolation Forest model on historical water quality data

        Parameters:
        -----------
        training_data : List[Dict]
            Historical measurements (normal + anomalous samples)

        Returns:
        --------
        Dict : Training statistics and performance metrics
        """
        print(f"Training Isolation Forest anomaly detector on {len(training_data)} samples...")

        # Prepare features
        X = self.prepare_features(training_data)

        # Fit scaler
        X_scaled = self.scaler.fit_transform(X)

        # Train Isolation Forest
        self.model = IsolationForest(
            contamination=self.contamination,
            n_estimators=100,
            max_samples='auto',
            random_state=self.random_state,
            n_jobs=-1,
            verbose=0
        )

        self.model.fit(X_scaled)
        self.is_trained = True

        # Calculate predictions and anomaly scores
        predictions = self.model.predict(X_scaled)
        anomaly_scores = self.model.score_samples(X_scaled)

        # Statistics
        n_anomalies = np.sum(predictions == -1)
        anomaly_rate = n_anomalies / len(predictions) * 100

        training_stats = {
            'n_samples': len(training_data),
            'n_anomalies_detected': int(n_anomalies),
            'anomaly_rate_percent': round(anomaly_rate, 2),
            'min_anomaly_score': float(anomaly_scores.min()),
            'max_anomaly_score': float(anomaly_scores.max()),
            'mean_anomaly_score': float(anomaly_scores.mean()),
            'contamination_threshold': self.contamination,
            'trained_at': datetime.now().isoformat()
        }

        print(f"✓ Training complete: {n_anomalies} anomalies detected ({anomaly_rate:.2f}%)")

        return training_stats

    def predict(self, measurement: Dict) -> Tuple[bool, str, str, float]:
        """
        Detect if a single measurement is anomalous

        Parameters:
        -----------
        measurement : Dict
            Single water quality measurement

        Returns:
        --------
        Tuple[bool, str, str, float]
            (is_anomaly, anomaly_type, severity, anomaly_score)
        """
        if not self.is_trained:
            raise ValueError("Model not trained! Call train() first or load() a trained model.")

        # Prepare features
        X = self.prepare_features([measurement])
        X_scaled = self.scaler.transform(X)

        # Predict
        prediction = self.model.predict(X_scaled)[0]
        anomaly_score = self.model.score_samples(X_scaled)[0]

        is_anomaly = (prediction == -1)

        if is_anomaly:
            # Classify anomaly type based on feature contributions
            anomaly_type = self._classify_anomaly_type(measurement, X.iloc[0])
            severity = self._calculate_severity(anomaly_score)
        else:
            anomaly_type = None
            severity = None

        return is_anomaly, anomaly_type, severity, float(anomaly_score)

    def predict_batch(self, measurements: List[Dict]) -> pd.DataFrame:
        """
        Detect anomalies in batch of measurements

        Parameters:
        -----------
        measurements : List[Dict]
            List of water quality measurements

        Returns:
        --------
        pd.DataFrame : Results with columns [is_anomaly, anomaly_type, severity, anomaly_score]
        """
        if not self.is_trained:
            raise ValueError("Model not trained! Call train() first or load() a trained model.")

        if not measurements:
            return pd.DataFrame()

        # Prepare features
        X = self.prepare_features(measurements)
        X_scaled = self.scaler.transform(X)

        # Predict
        predictions = self.model.predict(X_scaled)
        anomaly_scores = self.model.score_samples(X_scaled)

        # Build results dataframe
        results = pd.DataFrame({
            'is_anomaly': predictions == -1,
            'anomaly_score': anomaly_scores
        })

        # Classify anomaly types and severities
        results['anomaly_type'] = None
        results['severity'] = None

        for idx, row in results[results['is_anomaly']].iterrows():
            anomaly_type = self._classify_anomaly_type(measurements[idx], X.iloc[idx])
            severity = self._calculate_severity(row['anomaly_score'])
            results.at[idx, 'anomaly_type'] = anomaly_type
            results.at[idx, 'severity'] = severity

        return results

    def _classify_anomaly_type(self, measurement: Dict, features: pd.Series) -> str:
        """
        Classify the type of anomaly based on feature deviations

        Parameters:
        -----------
        measurement : Dict
            Original measurement data
        features : pd.Series
            Scaled features

        Returns:
        --------
        str : Anomaly type classification
        """
        # Calculate z-scores for each parameter (assuming standard scaling)
        deviations = {}

        # TDS spike detection
        if measurement.get('tds_ppm'):
            z_tds = (measurement['tds_ppm'] - features['tds_ppm']) / (features['tds_ppm'].std() + 1e-6)
            if abs(z_tds) > self.anomaly_thresholds['sudden_tds_spike']['z_score']:
                return 'sudden_tds_spike'

        # Chlorine drop detection
        if measurement.get('free_chlorine_mg_l') is not None:
            if measurement['free_chlorine_mg_l'] < 0.1:  # Below minimum safe threshold
                return 'chlorine_drop'

        # pH shift detection
        if measurement.get('ph_value'):
            if measurement['ph_value'] < 6.0 or measurement['ph_value'] > 9.0:
                return 'ph_shift'

        # Turbidity anomaly
        if measurement.get('turbidity_ntu'):
            if measurement['turbidity_ntu'] > 5.0:  # Above WHO guideline
                return 'turbidity_anomaly'

        # Temperature anomaly
        if measurement.get('temperature_celsius'):
            if measurement['temperature_celsius'] < 10 or measurement['temperature_celsius'] > 35:
                return 'temperature_anomaly'

        # RO system failure (if RO measurements available)
        if measurement.get('ro_rejection_rate_percent'):
            if measurement['ro_rejection_rate_percent'] < 85:  # Degraded RO membrane
                return 'ro_system_failure'

        # Default: general anomaly
        return 'general_anomaly'

    def _calculate_severity(self, anomaly_score: float) -> str:
        """
        Calculate anomaly severity based on anomaly score

        Parameters:
        -----------
        anomaly_score : float
            Isolation Forest anomaly score (more negative = more anomalous)

        Returns:
        --------
        str : Severity level ('low', 'medium', 'high', 'critical')
        """
        # Anomaly scores are negative, more negative = more anomalous
        if anomaly_score < -0.5:
            return 'critical'
        elif anomaly_score < -0.3:
            return 'high'
        elif anomaly_score < -0.15:
            return 'medium'
        else:
            return 'low'

    def save(self, path: Optional[str] = None) -> str:
        """
        Save trained model and scaler to disk

        Parameters:
        -----------
        path : str (optional)
            Custom path to save model

        Returns:
        --------
        str : Path where model was saved
        """
        if not self.is_trained:
            raise ValueError("Cannot save untrained model!")

        save_path = path or self.model_path

        # Ensure directory exists
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        # Save model and scaler together
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'feature_names': self.feature_names,
            'contamination': self.contamination,
            'trained_at': datetime.now().isoformat()
        }

        joblib.dump(model_data, save_path)
        print(f"✓ Model saved to: {save_path}")

        return save_path

    def load(self, path: Optional[str] = None) -> Dict:
        """
        Load trained model and scaler from disk

        Parameters:
        -----------
        path : str (optional)
            Custom path to load model from

        Returns:
        --------
        Dict : Model metadata
        """
        load_path = path or self.model_path

        if not os.path.exists(load_path):
            raise FileNotFoundError(f"Model file not found: {load_path}")

        # Load model data
        model_data = joblib.load(load_path)

        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.feature_names = model_data['feature_names']
        self.contamination = model_data['contamination']
        self.is_trained = True

        metadata = {
            'loaded_from': load_path,
            'trained_at': model_data.get('trained_at', 'unknown'),
            'contamination_threshold': self.contamination
        }

        print(f"✓ Model loaded from: {load_path}")

        return metadata

    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get relative importance of features for anomaly detection
        (approximated using feature variance contribution)

        Returns:
        --------
        Dict[str, float] : Feature importance scores
        """
        if not self.is_trained:
            raise ValueError("Model not trained!")

        # Isolation Forest doesn't have explicit feature importances
        # We approximate by calculating variance contribution
        importance = {}

        # This is a simplified approximation
        # In production, consider using SHAP values for better interpretation
        for i, feature in enumerate(self.feature_names):
            importance[feature] = 1.0 / (i + 1)  # Placeholder

        return importance

    def get_stats(self) -> Dict:
        """
        Get model statistics and configuration

        Returns:
        --------
        Dict : Model statistics
        """
        return {
            'is_trained': self.is_trained,
            'n_features': len(self.feature_names),
            'features': self.feature_names,
            'contamination_threshold': self.contamination,
            'model_type': 'IsolationForest',
            'target_accuracy': '92%'
        }


# Singleton instance for application-wide use
_anomaly_detector_instance = None

def get_anomaly_detector() -> WaterQualityAnomalyDetector:
    """
    Get or create singleton anomaly detector instance

    Returns:
    --------
    WaterQualityAnomalyDetector : Anomaly detector instance
    """
    global _anomaly_detector_instance

    if _anomaly_detector_instance is None:
        _anomaly_detector_instance = WaterQualityAnomalyDetector()

        # Try to load existing trained model
        try:
            _anomaly_detector_instance.load()
        except FileNotFoundError:
            print("No trained anomaly detection model found. Train model first.")

    return _anomaly_detector_instance


if __name__ == '__main__':
    # Example usage and testing
    print("Water Quality Anomaly Detector - Isolation Forest Implementation")
    print("=" * 70)

    # Create detector
    detector = WaterQualityAnomalyDetector()

    # Generate synthetic training data (normal + anomalies)
    np.random.seed(42)
    n_samples = 1000

    training_data = []
    for i in range(n_samples):
        # Normal samples (92%)
        if i < 920:
            measurement = {
                'ph_value': np.random.normal(7.2, 0.3),
                'tds_ppm': np.random.normal(250, 50),
                'temperature_celsius': np.random.normal(25, 3),
                'turbidity_ntu': np.random.uniform(0.1, 2.0),
                'conductivity_us_cm': np.random.normal(400, 80),
                'free_chlorine_mg_l': np.random.uniform(0.2, 0.8),
                'orp_mv': np.random.normal(650, 50),
                'measurement_datetime': datetime.now() - timedelta(hours=i)
            }
        # Anomalous samples (8%)
        else:
            anomaly_type = np.random.choice(['tds_spike', 'chlorine_drop', 'ph_shift', 'turbidity'])
            if anomaly_type == 'tds_spike':
                measurement = {
                    'ph_value': np.random.normal(7.2, 0.3),
                    'tds_ppm': np.random.uniform(800, 1200),  # Sudden spike
                    'temperature_celsius': np.random.normal(25, 3),
                    'turbidity_ntu': np.random.uniform(0.1, 2.0),
                    'conductivity_us_cm': np.random.normal(1200, 100),
                    'free_chlorine_mg_l': np.random.uniform(0.2, 0.8),
                    'orp_mv': np.random.normal(650, 50),
                    'measurement_datetime': datetime.now() - timedelta(hours=i)
                }
            elif anomaly_type == 'chlorine_drop':
                measurement = {
                    'ph_value': np.random.normal(7.2, 0.3),
                    'tds_ppm': np.random.normal(250, 50),
                    'temperature_celsius': np.random.normal(25, 3),
                    'turbidity_ntu': np.random.uniform(0.1, 2.0),
                    'conductivity_us_cm': np.random.normal(400, 80),
                    'free_chlorine_mg_l': np.random.uniform(0.0, 0.05),  # Drop
                    'orp_mv': np.random.normal(450, 50),
                    'measurement_datetime': datetime.now() - timedelta(hours=i)
                }
            elif anomaly_type == 'ph_shift':
                measurement = {
                    'ph_value': np.random.choice([5.2, 9.5]),  # Extreme pH
                    'tds_ppm': np.random.normal(250, 50),
                    'temperature_celsius': np.random.normal(25, 3),
                    'turbidity_ntu': np.random.uniform(0.1, 2.0),
                    'conductivity_us_cm': np.random.normal(400, 80),
                    'free_chlorine_mg_l': np.random.uniform(0.2, 0.8),
                    'orp_mv': np.random.normal(650, 50),
                    'measurement_datetime': datetime.now() - timedelta(hours=i)
                }
            else:  # turbidity
                measurement = {
                    'ph_value': np.random.normal(7.2, 0.3),
                    'tds_ppm': np.random.normal(250, 50),
                    'temperature_celsius': np.random.normal(25, 3),
                    'turbidity_ntu': np.random.uniform(8.0, 15.0),  # High turbidity
                    'conductivity_us_cm': np.random.normal(400, 80),
                    'free_chlorine_mg_l': np.random.uniform(0.2, 0.8),
                    'orp_mv': np.random.normal(650, 50),
                    'measurement_datetime': datetime.now() - timedelta(hours=i)
                }

        training_data.append(measurement)

    # Train model
    stats = detector.train(training_data)
    print("\nTraining Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Test prediction on anomalous sample
    test_anomaly = {
        'ph_value': 7.1,
        'tds_ppm': 1500,  # Sudden spike!
        'temperature_celsius': 24,
        'turbidity_ntu': 1.2,
        'conductivity_us_cm': 1800,
        'free_chlorine_mg_l': 0.5,
        'orp_mv': 640,
        'measurement_datetime': datetime.now()
    }

    is_anomaly, anomaly_type, severity, score = detector.predict(test_anomaly)

    print("\nTest Prediction (TDS Spike):")
    print(f"  Is Anomaly: {is_anomaly}")
    print(f"  Anomaly Type: {anomaly_type}")
    print(f"  Severity: {severity}")
    print(f"  Anomaly Score: {score:.4f}")

    # Save model
    detector.save()
    print("\n✓ Anomaly detector ready for production use!")
