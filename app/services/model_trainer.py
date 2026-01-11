"""ML Model Training Service - Actual sklearn/XGBoost Training

This module implements real machine learning model training to replace
the rule-based predictions. Supports incremental/rolling training.
"""

import os
import joblib
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor, IsolationForest
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, r2_score
import xgboost as xgb


class ModelTrainer:
    """Train and persist ML models for water quality prediction"""

    def __init__(self, models_path: str = None):
        """Initialize model trainer

        Args:
            models_path: Directory to save/load models (default: app/ml/models/)
        """
        if models_path is None:
            # Default to app/ml/models/ relative to this file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            models_path = os.path.join(os.path.dirname(current_dir), 'ml', 'models')

        self.models_path = models_path
        os.makedirs(self.models_path, exist_ok=True)

        # Encoders for categorical features
        self.label_encoders = {}
        self.scalers = {}

        # Model hyperparameters (from ML_RUN_VECTOR_SPECIFICATION)
        self.model_configs = {
            'site_risk': {
                'n_estimators': 100,
                'max_depth': 8,
                'min_samples_split': 10,
                'class_weight': 'balanced',
                'random_state': 42
            },
            'contamination': {
                'n_estimators': 100,
                'max_depth': 6,
                'learning_rate': 0.1,
                'subsample': 0.8,
                'colsample_bytree': 0.8,
                'objective': 'multi:softprob',
                'eval_metric': 'mlogloss',
                'random_state': 42
            },
            'wqi': {
                'n_estimators': 100,
                'max_depth': 6,
                'learning_rate': 0.1,
                'random_state': 42
            },
            'anomaly': {
                'n_estimators': 100,
                'contamination': 0.1,
                'random_state': 42
            }
        }

    # ========================================================================
    # MODEL 1: SITE RISK CLASSIFIER (Random Forest)
    # ========================================================================

    def train_site_risk_model(self, training_data: List[Dict], training_labels: List[str]) -> Dict:
        """Train Random Forest for site risk classification

        Args:
            training_data: List of site feature dictionaries
            training_labels: List of risk levels ['critical', 'high', 'medium', 'low']

        Returns:
            Dict with model, accuracy, and metadata
        """
        print(f"Training Site Risk Classifier on {len(training_data)} samples...")

        # Prepare features
        X_train, feature_names = self._prepare_site_features(training_data)

        # Encode labels
        if 'site_risk_labels' not in self.label_encoders:
            self.label_encoders['site_risk_labels'] = LabelEncoder()
            self.label_encoders['site_risk_labels'].fit(['low', 'medium', 'high', 'critical'])

        y_train = self.label_encoders['site_risk_labels'].transform(training_labels)

        # Train Random Forest
        model = RandomForestClassifier(**self.model_configs['site_risk'])
        model.fit(X_train, y_train)

        # Calculate training accuracy
        y_pred = model.predict(X_train)
        accuracy = accuracy_score(y_train, y_pred)

        # Feature importance
        feature_importance = dict(zip(feature_names, model.feature_importances_))

        # Save model
        model_data = {
            'model': model,
            'label_encoder': self.label_encoders['site_risk_labels'],
            'feature_names': feature_names,
            'feature_importance': feature_importance,
            'training_accuracy': accuracy,
            'training_samples': len(training_data),
            'training_timestamp': datetime.utcnow().isoformat(),
            'model_version': 'rf_v1',
            'hyperparameters': self.model_configs['site_risk']
        }

        self._save_model(model_data, 'site_risk_classifier')

        print(f"✓ Site Risk Classifier trained: {accuracy:.3f} accuracy")

        return model_data

    def _prepare_site_features(self, training_data: List[Dict]) -> Tuple[np.ndarray, List[str]]:
        """Extract and encode site features for Random Forest

        Features (from ML_RUN_VECTOR_SPECIFICATION):
        - site_type (one-hot encoded)
        - is_industrial_nearby (boolean → 0/1)
        - is_agricultural_nearby (boolean → 0/1)
        - is_coastal (boolean → 0/1)
        - is_urban (boolean → 0/1)
        - contamination_rate_30d (float 0-100)
        - days_since_last_test (int)
        """
        feature_names = [
            'is_industrial_nearby',
            'is_agricultural_nearby',
            'is_coastal',
            'is_urban',
            'contamination_rate_30d',
            'days_since_last_test',
            'site_type_stepwell',
            'site_type_tank',
            'site_type_pond',
            'site_type_lake'
        ]

        features = []
        for data in training_data:
            site_type = data.get('site_type', '').lower()

            feature_row = [
                1 if data.get('is_industrial_nearby') else 0,
                1 if data.get('is_agricultural_nearby') else 0,
                1 if data.get('is_coastal') else 0,
                1 if data.get('is_urban') else 0,
                float(data.get('contamination_rate_30d', 0)),
                int(data.get('days_since_last_test', 30)),
                # One-hot encoding for site_type
                1 if site_type == 'stepwell' else 0,
                1 if site_type == 'tank' else 0,
                1 if site_type == 'pond' else 0,
                1 if site_type == 'lake' else 0
            ]
            features.append(feature_row)

        return np.array(features), feature_names

    # ========================================================================
    # MODEL 2: CONTAMINATION TYPE CLASSIFIER (XGBoost)
    # ========================================================================

    def train_contamination_model(self, training_data: List[Dict], training_labels: List[str]) -> Dict:
        """Train XGBoost for contamination type classification

        Args:
            training_data: List of test result feature dictionaries
            training_labels: List of contamination types
                ['runoff_sediment', 'sewage_ingress', 'salt_intrusion',
                 'pipe_corrosion', 'disinfectant_decay']

        Returns:
            Dict with model, F1 score, and metadata
        """
        print(f"Training Contamination Classifier on {len(training_data)} samples...")

        # Prepare features
        X_train, feature_names = self._prepare_test_result_features(training_data)

        # Encode labels - fit on actual training labels
        if 'contamination_labels' not in self.label_encoders:
            self.label_encoders['contamination_labels'] = LabelEncoder()

        # Fit on actual training labels (not predefined classes)
        self.label_encoders['contamination_labels'].fit(training_labels)
        y_train = self.label_encoders['contamination_labels'].transform(training_labels)

        # Check if we have at least 2 classes
        n_classes = len(set(training_labels))
        if n_classes < 2:
            print(f"⚠ Warning: Only {n_classes} contamination type(s) in training data.")
            print(f"  XGBoost requires at least 2 classes for classification.")
            print(f"  Skipping contamination model training.")
            return None

        # Train XGBoost
        model = xgb.XGBClassifier(**self.model_configs['contamination'])
        model.fit(X_train, y_train)

        # Calculate metrics
        y_pred = model.predict(X_train)
        accuracy = accuracy_score(y_train, y_pred)
        f1 = f1_score(y_train, y_pred, average='weighted')

        # Feature importance
        feature_importance = dict(zip(feature_names, model.feature_importances_))

        # Save model
        model_data = {
            'model': model,
            'label_encoder': self.label_encoders['contamination_labels'],
            'feature_names': feature_names,
            'feature_importance': feature_importance,
            'training_accuracy': accuracy,
            'training_f1': f1,
            'training_samples': len(training_data),
            'training_timestamp': datetime.utcnow().isoformat(),
            'model_version': 'xgb_v1',
            'hyperparameters': self.model_configs['contamination']
        }

        self._save_model(model_data, 'contamination_classifier')

        print(f"✓ Contamination Classifier trained: {f1:.3f} F1, {accuracy:.3f} accuracy")

        return model_data

    def _prepare_test_result_features(self, training_data: List[Dict]) -> Tuple[np.ndarray, List[str]]:
        """Extract and normalize test result features for XGBoost

        Features (from ML_RUN_VECTOR_SPECIFICATION):
        - pH, turbidity, TDS, chlorine, iron, manganese, coliform, ammonia, chloride
        - rained_recently (boolean)
        - is_coastal (boolean)
        """
        feature_names = [
            'ph', 'turbidity', 'tds', 'chlorine', 'iron', 'manganese',
            'coliform', 'ammonia', 'chloride', 'rained_recently', 'is_coastal'
        ]

        features = []
        for data in training_data:
            feature_row = [
                float(data.get('ph', 7.0)),
                float(data.get('turbidity', 0)),
                float(data.get('tds', 0)),
                float(data.get('chlorine', 0)),
                float(data.get('iron', 0)),
                float(data.get('manganese', 0)),
                float(data.get('coliform', 0)),
                float(data.get('ammonia', 0)),
                float(data.get('chloride', 0)),
                1 if data.get('rained_recently') else 0,
                1 if data.get('is_coastal') else 0
            ]
            features.append(feature_row)

        X = np.array(features)

        # Normalize features (XGBoost benefits from scaling)
        if 'contamination_scaler' not in self.scalers:
            self.scalers['contamination_scaler'] = StandardScaler()
            self.scalers['contamination_scaler'].fit(X)

        X_scaled = self.scalers['contamination_scaler'].transform(X)

        return X_scaled, feature_names

    # ========================================================================
    # MODEL 3: WQI PREDICTOR (Gradient Boosting Regressor)
    # ========================================================================

    def train_wqi_model(self, training_data: List[Dict], training_labels: List[float]) -> Dict:
        """Train Gradient Boosting for WQI prediction

        Args:
            training_data: List of test result feature dictionaries
            training_labels: List of WQI scores (0-100)

        Returns:
            Dict with model, MAE, R², and metadata
        """
        print(f"Training WQI Predictor on {len(training_data)} samples...")

        # Prepare features (same as contamination model)
        X_train, feature_names = self._prepare_test_result_features(training_data)
        y_train = np.array(training_labels)

        # Train Gradient Boosting Regressor
        model = GradientBoostingRegressor(**self.model_configs['wqi'])
        model.fit(X_train, y_train)

        # Calculate metrics
        y_pred = model.predict(X_train)
        mae = mean_absolute_error(y_train, y_pred)
        r2 = r2_score(y_train, y_pred)

        # Feature importance
        feature_importance = dict(zip(feature_names, model.feature_importances_))

        # Save model
        model_data = {
            'model': model,
            'scaler': self.scalers.get('contamination_scaler'),  # Reuse scaler
            'feature_names': feature_names,
            'feature_importance': feature_importance,
            'training_mae': mae,
            'training_r2': r2,
            'training_samples': len(training_data),
            'training_timestamp': datetime.utcnow().isoformat(),
            'model_version': 'gbr_v1',
            'hyperparameters': self.model_configs['wqi']
        }

        self._save_model(model_data, 'wqi_predictor')

        print(f"✓ WQI Predictor trained: MAE={mae:.2f}, R²={r2:.3f}")

        return model_data

    # ========================================================================
    # MODEL 5: ANOMALY DETECTOR (Isolation Forest)
    # ========================================================================

    def train_anomaly_detector(self, training_data: List[Dict]) -> Dict:
        """Train Isolation Forest for anomaly detection

        Args:
            training_data: List of test result feature dictionaries (normal samples only)

        Returns:
            Dict with model and metadata
        """
        print(f"Training Anomaly Detector on {len(training_data)} samples...")

        # Prepare features
        X_train, feature_names = self._prepare_test_result_features(training_data)

        # Train Isolation Forest (unsupervised)
        model = IsolationForest(**self.model_configs['anomaly'])
        model.fit(X_train)

        # Calculate training anomaly rate
        y_pred = model.predict(X_train)
        anomaly_rate = np.sum(y_pred == -1) / len(y_pred) * 100

        # Save model
        model_data = {
            'model': model,
            'scaler': self.scalers.get('contamination_scaler'),
            'feature_names': feature_names,
            'training_anomaly_rate': anomaly_rate,
            'training_samples': len(training_data),
            'training_timestamp': datetime.utcnow().isoformat(),
            'model_version': 'iforest_v1',
            'hyperparameters': self.model_configs['anomaly']
        }

        self._save_model(model_data, 'anomaly_detector')

        print(f"✓ Anomaly Detector trained: {anomaly_rate:.1f}% anomaly rate in training")

        return model_data

    # ========================================================================
    # MODEL PERSISTENCE
    # ========================================================================

    def _save_model(self, model_data: Dict, model_name: str):
        """Save model to disk with joblib

        Args:
            model_data: Dict containing model and metadata
            model_name: Name for the model file (e.g., 'site_risk_classifier')
        """
        model_file = os.path.join(self.models_path, f'{model_name}.joblib')
        joblib.dump(model_data, model_file)
        print(f"  → Saved to {model_file}")

    def load_model(self, model_name: str) -> Optional[Dict]:
        """Load model from disk

        Args:
            model_name: Name of the model file (without .joblib extension)

        Returns:
            Dict with model and metadata, or None if not found
        """
        model_file = os.path.join(self.models_path, f'{model_name}.joblib')

        if not os.path.exists(model_file):
            print(f"Model file not found: {model_file}")
            return None

        model_data = joblib.load(model_file)
        print(f"✓ Loaded {model_name} from {model_file}")

        return model_data

    # ========================================================================
    # PREDICTION METHODS (for use after training)
    # ========================================================================

    def predict_site_risk(self, site_features: Dict, model_data: Dict) -> Dict:
        """Predict site risk using trained Random Forest

        Args:
            site_features: Site feature dictionary
            model_data: Loaded model data from load_model()

        Returns:
            Prediction dict with risk_level, risk_score, confidence
        """
        model = model_data['model']
        label_encoder = model_data['label_encoder']

        # Prepare features
        X, _ = self._prepare_site_features([site_features])

        # Predict
        y_pred = model.predict(X)[0]
        y_proba = model.predict_proba(X)[0]

        risk_level = label_encoder.inverse_transform([y_pred])[0]
        confidence = np.max(y_proba)

        # Map to risk score (0-100)
        risk_score_map = {'low': 25, 'medium': 50, 'high': 75, 'critical': 95}
        risk_score = risk_score_map.get(risk_level, 50)

        return {
            'risk_level': risk_level,
            'risk_score': risk_score,
            'confidence': confidence,
            'model_version': model_data['model_version'],
            'probabilities': {
                label: float(prob)
                for label, prob in zip(label_encoder.classes_, y_proba)
            }
        }

    def predict_contamination(self, test_result: Dict, model_data: Dict) -> Dict:
        """Predict contamination type using trained XGBoost

        Args:
            test_result: Test result feature dictionary
            model_data: Loaded model data from load_model()

        Returns:
            Prediction dict with contamination type, confidence, probabilities
        """
        model = model_data['model']
        label_encoder = model_data['label_encoder']

        # Prepare features
        X, _ = self._prepare_test_result_features([test_result])

        # Predict
        y_pred = model.predict(X)[0]
        y_proba = model.predict_proba(X)[0]

        contamination_type = label_encoder.inverse_transform([y_pred])[0]
        confidence = np.max(y_proba)

        return {
            'predicted_type': contamination_type,
            'confidence': confidence,
            'model_version': model_data['model_version'],
            'probabilities': {
                label: float(prob)
                for label, prob in zip(label_encoder.classes_, y_proba)
            }
        }

    def predict_wqi(self, test_result: Dict, model_data: Dict) -> Dict:
        """Predict WQI using trained Gradient Boosting

        Args:
            test_result: Test result feature dictionary
            model_data: Loaded model data from load_model()

        Returns:
            Prediction dict with WQI score
        """
        model = model_data['model']

        # Prepare features
        X, _ = self._prepare_test_result_features([test_result])

        # Predict
        wqi_score = model.predict(X)[0]
        wqi_score = np.clip(wqi_score, 0, 100)  # Ensure valid range

        # Classify
        if wqi_score >= 90:
            wqi_class = 'Excellent'
        elif wqi_score >= 70:
            wqi_class = 'Compliant'
        elif wqi_score >= 50:
            wqi_class = 'Warning'
        else:
            wqi_class = 'Unsafe'

        return {
            'wqi_score': float(wqi_score),
            'wqi_class': wqi_class,
            'is_drinkable': wqi_score >= 70,
            'model_version': model_data['model_version']
        }

    def detect_anomaly(self, test_result: Dict, model_data: Dict) -> Dict:
        """Detect anomaly using trained Isolation Forest

        Args:
            test_result: Test result feature dictionary
            model_data: Loaded model data from load_model()

        Returns:
            Prediction dict with anomaly status and score
        """
        model = model_data['model']

        # Prepare features
        X, _ = self._prepare_test_result_features([test_result])

        # Predict (-1 = anomaly, 1 = normal)
        y_pred = model.predict(X)[0]
        anomaly_score = model.decision_function(X)[0]

        is_anomaly = (y_pred == -1)

        # Normalize score to 0-1 range (lower = more anomalous)
        # decision_function returns negative values for anomalies
        normalized_score = 1 / (1 + np.exp(-anomaly_score))  # Sigmoid

        return {
            'is_anomaly': bool(is_anomaly),
            'anomaly_score': float(normalized_score),
            'anomaly_type': 'spike' if is_anomaly else None,
            'model_version': model_data['model_version']
        }
