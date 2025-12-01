"""
ML API Client - Integration with central ML model for contamination prediction
"""
import requests
import json
from flask import current_app


class MLAPIClient:
    """Client for interacting with the ML contamination prediction API"""

    def __init__(self):
        self.api_url = current_app.config.get('ML_MODEL_API_URL', '')
        self.api_key = current_app.config.get('ML_MODEL_API_KEY', '')
        self.timeout = 30  # seconds

    def predict_contamination(self, sample, test_result):
        """
        Send sample and test data to ML API for prediction
        Returns dict with prediction results or error info
        """
        if not self.api_url:
            return {
                'success': False,
                'error': 'ML API URL not configured'
            }

        try:
            # Prepare payload
            payload = self._prepare_payload(sample, test_result)

            # Make API request
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {self.api_key}' if self.api_key else ''
            }

            response = requests.post(
                f"{self.api_url}/predict",
                json=payload,
                headers=headers,
                timeout=self.timeout
            )

            response.raise_for_status()

            # Parse response
            result = response.json()

            return {
                'success': True,
                'prediction': result.get('prediction'),
                'confidence': result.get('confidence'),
                'model_version': result.get('model_version'),
                'recommendations': result.get('recommendations', []),
                'full_response': result
            }

        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'ML API request timed out'
            }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'error': 'Could not connect to ML API'
            }
        except requests.exceptions.HTTPError as e:
            return {
                'success': False,
                'error': f'ML API returned error: {e.response.status_code}'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }

    def _prepare_payload(self, sample, test_result):
        """Prepare data payload for ML API"""
        payload = {
            'sample_data': {
                'sample_id': sample.sample_id,
                'site_code': sample.site.site_code if sample.site else None,
                'environment_type': sample.site.environment_type if sample.site else None,
                'is_coastal': sample.site.is_coastal if sample.site else False,
                'source_type': sample.source_type,
                'source_depth_meters': sample.source_depth_meters,
                'storage_type': sample.storage_type,
                'storage_material': sample.storage_material,
                'discharge_type': sample.discharge_type,
                'pipe_material': sample.pipe_material,
                'pipe_age_years': sample.pipe_age_years,
                'distance_from_source_meters': sample.distance_from_source_meters,
                'weather_condition': sample.weather_condition,
                'rained_recently': sample.rained_recently,
                'days_since_rain': sample.days_since_rain,
                'water_appearance': sample.water_appearance,
                'odor_present': sample.odor_present,
                'visible_particles': sample.visible_particles
            },
            'test_data': test_result.get_parameters_dict(),
            'metadata': {
                'collection_date': sample.collection_date.isoformat() if sample.collection_date else None,
                'test_date': test_result.test_date.isoformat() if test_result.test_date else None
            }
        }

        return payload

    def get_model_info(self):
        """Get information about the ML model"""
        if not self.api_url:
            return {'success': False, 'error': 'ML API URL not configured'}

        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}' if self.api_key else ''
            }

            response = requests.get(
                f"{self.api_url}/info",
                headers=headers,
                timeout=self.timeout
            )

            response.raise_for_status()
            return {'success': True, 'data': response.json()}

        except Exception as e:
            return {'success': False, 'error': str(e)}
