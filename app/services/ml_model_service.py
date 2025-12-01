"""
ML Model Service for Site Risk and Contamination Prediction
Loads trained models and provides inference capabilities
"""

import os
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class MLModelService:
    """Service for loading and using trained ML models"""

    def __init__(self, model_dir: str = None):
        """
        Initialize ML Model Service

        Args:
            model_dir: Directory containing trained models
        """
        if model_dir is None:
            # Default to app/ml/trained_models/
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_dir = os.path.join(base_dir, 'ml', 'trained_models')

        self.model_dir = model_dir
        self.site_risk_model = None
        self.contamination_model = None
        self.models_loaded = False

        logger.info(f"ML Model Service initialized with model_dir: {model_dir}")

    def load_models(self) -> bool:
        """
        Load all trained ML models

        Returns:
            True if models loaded successfully, False otherwise
        """
        try:
            import joblib

            # Load site risk classifier
            site_risk_path = os.path.join(self.model_dir, 'site_risk_classifier.pkl')
            if os.path.exists(site_risk_path):
                self.site_risk_model = joblib.load(site_risk_path)
                logger.info("✓ Loaded site risk classifier")
            else:
                logger.warning(f"Site risk model not found at {site_risk_path}")

            # Load contamination classifier (saved as dict with model, label_encoder, feature_cols)
            contamination_path = os.path.join(self.model_dir, 'contamination_classifier.pkl')
            if os.path.exists(contamination_path):
                self.contamination_model = joblib.load(contamination_path)
                logger.info("✓ Loaded contamination classifier")
            else:
                logger.warning(f"Contamination model not found at {contamination_path}")

            self.models_loaded = True
            return True

        except Exception as e:
            logger.error(f"Error loading models: {e}", exc_info=True)
            return False

    def predict_site_risk(self, site_data: Dict) -> Dict:
        """
        Predict risk level for a site

        Args:
            site_data: Dictionary containing site features

        Returns:
            Dictionary with prediction results
        """
        if not self.models_loaded:
            self.load_models()

        if self.site_risk_model is None:
            return {
                'success': False,
                'error': 'Site risk model not loaded'
            }

        try:
            # Extract and prepare features
            features = self._prepare_site_features(site_data)

            # Make prediction
            prediction = self.site_risk_model.predict([features])[0]
            probabilities = self.site_risk_model.predict_proba([features])[0]

            # Get class probabilities
            classes = self.site_risk_model.classes_
            risk_probabilities = {
                cls: float(prob) for cls, prob in zip(classes, probabilities)
            }

            # Determine confidence
            max_prob = max(probabilities)
            confidence = 'high' if max_prob > 0.7 else 'medium' if max_prob > 0.5 else 'low'

            return {
                'success': True,
                'risk_level': prediction,
                'probabilities': risk_probabilities,
                'confidence': confidence,
                'max_probability': float(max_prob),
                'recommendation': self._get_risk_recommendation(prediction)
            }

        except Exception as e:
            logger.error(f"Error predicting site risk: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def predict_contamination_type(self, sample_data: Dict) -> Dict:
        """
        Predict likely contamination type for a water sample

        Args:
            sample_data: Dictionary containing sample test results

        Returns:
            Dictionary with prediction results
        """
        if not self.models_loaded:
            self.load_models()

        if self.contamination_model is None:
            return {
                'success': False,
                'error': 'Contamination model not loaded'
            }

        try:
            # Handle dict format (model saved as dict with 'model', 'label_encoder', 'feature_cols')
            if isinstance(self.contamination_model, dict):
                model = self.contamination_model['model']
                label_encoder = self.contamination_model.get('label_encoder')
            else:
                model = self.contamination_model
                label_encoder = None

            # Extract and prepare features
            features = self._prepare_sample_features(sample_data)

            # Make prediction
            prediction_encoded = model.predict([features])[0]
            probabilities = model.predict_proba([features])[0]

            # Decode prediction if label encoder available
            if label_encoder:
                prediction = label_encoder.inverse_transform([prediction_encoded])[0]
                classes = label_encoder.classes_
            else:
                prediction = prediction_encoded
                classes = model.classes_

            # Get class probabilities
            contamination_probabilities = {
                cls: float(prob) for cls, prob in zip(classes, probabilities)
            }

            # Get top contaminants
            sorted_contaminants = sorted(
                contamination_probabilities.items(),
                key=lambda x: x[1],
                reverse=True
            )

            return {
                'success': True,
                'primary_contamination': prediction,
                'probabilities': contamination_probabilities,
                'top_contaminants': [
                    {'type': cont, 'probability': prob}
                    for cont, prob in sorted_contaminants[:3]
                ],
                'recommendation': self._get_contamination_recommendation(prediction)
            }

        except Exception as e:
            logger.error(f"Error predicting contamination type: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def _prepare_site_features(self, site_data: Dict) -> np.ndarray:
        """
        Prepare feature vector for site risk prediction
        Must match training pipeline exactly - 21 features total

        Args:
            site_data: Raw site data

        Returns:
            Feature vector as numpy array (21 features)
        """
        # Map environment types to encoded values (from training)
        env_type_map = {
            'Urban': 0,
            'Industrial': 1,
            'Semi-Urban': 2,
            'Rural Agricultural': 3,
            'Rural': 4
        }

        # Map water body types (if available)
        water_body_map = {
            'River': 0,
            'Lake': 1,
            'Reservoir': 2,
            'Groundwater': 3,
            'Ocean': 4
        }

        # Map states (simplified - use first 10 common states)
        state_map = {
            'Maharashtra': 0,
            'Karnataka': 1,
            'Tamil Nadu': 2,
            'Gujarat': 3,
            'Rajasthan': 4,
            'Uttar Pradesh': 5,
            'West Bengal': 6,
            'Kerala': 7,
            'Punjab': 8,
            'Delhi': 9
        }

        # Extract features in expected order (must match training)
        features = []

        # 1. environment_type_encoded
        features.append(env_type_map.get(site_data.get('environment_type', 'Urban'), 0))

        # 2. water_body_type_encoded
        features.append(water_body_map.get(site_data.get('water_body_type', 'Groundwater'), 3))

        # 3. state_encoded
        features.append(state_map.get(site_data.get('state', 'Maharashtra'), 0))

        # 4. is_coastal_binary
        features.append(int(site_data.get('is_coastal', False)))

        # 5. industrial_nearby_binary
        features.append(int(site_data.get('industrial_nearby', False)))

        # 6. agricultural_nearby_binary
        features.append(int(site_data.get('agricultural_nearby', False)))

        # 7. pop_density_log
        pop_density = site_data.get('population_density')
        if pop_density is None or pop_density == 0:
            pop_density = 1000  # Default value
        features.append(np.log1p(pop_density))

        # 8. is_high_density
        features.append(1 if pop_density > 5000 else 0)

        # Historical contamination statistics (9-21: 13 features)
        # Use defaults if not available

        # 9. hist_overall_quality_score_mean
        features.append(site_data.get('hist_overall_quality_score_mean', 0.7))

        # 10. hist_overall_quality_score_std
        features.append(site_data.get('hist_overall_quality_score_std', 0.15))

        # 11. hist_overall_quality_score_min
        features.append(site_data.get('hist_overall_quality_score_min', 0.5))

        # 12. hist_runoff_sediment_score_mean
        features.append(site_data.get('hist_runoff_sediment_score_mean', 0.1))

        # 13. hist_sewage_ingress_score_mean
        features.append(site_data.get('hist_sewage_ingress_score_mean', 0.05))

        # 14. hist_salt_intrusion_score_mean
        features.append(site_data.get('hist_salt_intrusion_score_mean', 0.05))

        # 15. hist_pipe_corrosion_score_mean
        features.append(site_data.get('hist_pipe_corrosion_score_mean', 0.05))

        # 16. hist_disinfectant_decay_score_mean
        features.append(site_data.get('hist_disinfectant_decay_score_mean', 0.05))

        # 17. hist_who_compliant_mean
        features.append(site_data.get('hist_who_compliant_mean', 0.8))

        # 18. hist_follow_up_required_sum
        features.append(site_data.get('hist_follow_up_required_sum', 0))

        # 19-21. Additional historical features (use reasonable defaults)
        features.append(site_data.get('hist_contamination_rate', 0.1))
        features.append(site_data.get('hist_sample_count', 10))
        features.append(site_data.get('hist_days_since_last_test', 30))

        return np.array(features)

    def _prepare_sample_features(self, sample_data: Dict) -> np.ndarray:
        """
        Prepare feature vector for contamination prediction

        Args:
            sample_data: Raw sample test data

        Returns:
            Feature vector as numpy array
        """
        features = []

        # Water quality parameters
        features.append(sample_data.get('ph', 7.0))
        features.append(sample_data.get('turbidity', 5.0))
        features.append(sample_data.get('tds', 500.0))
        features.append(sample_data.get('dissolved_oxygen', 5.0))
        features.append(sample_data.get('temperature', 25.0))
        features.append(sample_data.get('nitrate', 10.0))
        features.append(sample_data.get('total_hardness', 200.0))
        features.append(sample_data.get('bod', 5.0))
        features.append(sample_data.get('cod', 20.0))
        features.append(sample_data.get('chloride', 100.0))
        features.append(sample_data.get('iron', 0.1))
        features.append(sample_data.get('arsenic', 0.005))
        features.append(sample_data.get('lead', 0.005))

        # Derived features
        bod = sample_data.get('bod', 5.0)
        cod = sample_data.get('cod', 20.0)
        features.append(bod / (cod + 0.1))  # BOD/COD ratio

        hardness = sample_data.get('total_hardness', 200.0)
        tds = sample_data.get('tds', 500.0)
        features.append(hardness / (tds + 1))  # Hardness/TDS ratio

        # Contamination indicators
        features.append(1 if sample_data.get('turbidity', 5) > 10 else 0)
        features.append(1 if sample_data.get('nitrate', 10) > 45 else 0)
        features.append(1 if sample_data.get('tds', 500) > 500 else 0)
        features.append(1 if sample_data.get('coliform_status') == 'present' else 0)
        features.append(1 if sample_data.get('iron', 0.1) > 0.3 else 0)
        features.append(1 if sample_data.get('arsenic', 0.005) > 0.01 else 0)
        features.append(1 if sample_data.get('lead', 0.005) > 0.01 else 0)

        # Seasonal features (if collection_date provided)
        if 'collection_date' in sample_data:
            date = pd.to_datetime(sample_data['collection_date'])
            month = date.month
            is_monsoon = 1 if month in [6, 7, 8, 9] else 0
            features.append(is_monsoon)
        else:
            features.append(0)

        return np.array(features)

    def _get_risk_recommendation(self, risk_level: str) -> str:
        """Get recommendation based on risk level"""
        recommendations = {
            'high': 'Implement frequent testing (weekly). Priority monitoring required. Consider enhanced treatment.',
            'medium': 'Regular testing recommended (bi-weekly to monthly). Monitor quality trends.',
            'low': 'Standard testing schedule (quarterly). Maintain routine monitoring.'
        }
        return recommendations.get(risk_level, 'Continue routine monitoring.')

    def _get_contamination_recommendation(self, contamination_type: str) -> str:
        """Get recommendation based on contamination type"""
        recommendations = {
            'runoff_sediment': 'Implement filtration. Check upstream for sediment sources. Consider seasonal patterns.',
            'sewage_ingress': 'IMMEDIATE ACTION REQUIRED. Disinfect system. Identify and repair sewage leak. Test for pathogens.',
            'salt_intrusion': 'Monitor chloride levels. Check for seawater intrusion. May need alternative source.',
            'pipe_corrosion': 'Replace corroded pipes. Adjust pH. Monitor heavy metals (iron, lead, copper).',
            'disinfectant_decay': 'Increase chlorine dosing. Check distribution system. Reduce water age in pipes.'
        }
        return recommendations.get(contamination_type, 'Consult water quality specialist for detailed analysis.')

    def batch_predict_site_risks(self, sites_data: List[Dict]) -> List[Dict]:
        """
        Predict risk levels for multiple sites

        Args:
            sites_data: List of site data dictionaries

        Returns:
            List of prediction results
        """
        results = []
        for site in sites_data:
            prediction = self.predict_site_risk(site)
            prediction['site_code'] = site.get('site_code')
            results.append(prediction)
        return results

    def get_model_info(self) -> Dict:
        """
        Get information about loaded models

        Returns:
            Dictionary with model information
        """
        if not self.models_loaded:
            self.load_models()

        site_risk_loaded = self.site_risk_model is not None
        contamination_loaded = self.contamination_model is not None

        # Handle contamination model dict format
        if contamination_loaded and isinstance(self.contamination_model, dict):
            contam_model = self.contamination_model.get('model')
            contam_type = str(type(contam_model).__name__) if contam_model else None
            contam_encoder = self.contamination_model.get('label_encoder')
            contam_classes = list(contam_encoder.classes_) if contam_encoder and hasattr(contam_encoder, 'classes_') else None
        else:
            contam_model = self.contamination_model
            contam_type = str(type(contam_model).__name__) if contam_model else None
            contam_classes = list(contam_model.classes_) if contam_model and hasattr(contam_model, 'classes_') else None

        info = {
            'models_loaded': self.models_loaded,
            'model_dir': self.model_dir,
            'site_risk_model': {
                'loaded': site_risk_loaded,
                'type': str(type(self.site_risk_model).__name__) if site_risk_loaded else None,
                'classes': list(self.site_risk_model.classes_) if site_risk_loaded and hasattr(self.site_risk_model, 'classes_') else None
            },
            'contamination_model': {
                'loaded': contamination_loaded,
                'type': contam_type,
                'classes': contam_classes
            }
        }

        return info


# Global instance
_model_service = None


def get_model_service() -> MLModelService:
    """Get or create global model service instance"""
    global _model_service
    if _model_service is None:
        _model_service = MLModelService()
        _model_service.load_models()
    return _model_service
