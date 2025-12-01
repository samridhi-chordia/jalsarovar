"""
WFLOW-ML: Gaussian Process Water Quality Prediction
Spatial-Temporal Surrogate Model for Parameter Estimation

This module implements Gaussian Process Regression (GPR) for water quality
prediction across spatial and temporal dimensions:

Applications:
- Predict water quality parameters at unmeasured locations
- Interpolate between sparse sampling points
- Quantify prediction uncertainty
- Identify high-risk areas requiring testing
- Reduce testing requirements while maintaining accuracy

Methodology:
- Gaussian Process with RBF + Matérn kernels
- Input features: [latitude, longitude, month, distance_to_source, elevation]
- Multi-output GPR for correlated parameters (pH, TDS, etc.)
- Active learning via uncertainty-based sampling

Author: Jal Sarovar Development Team
Date: November 17, 2025
License: MIT
"""

import logging
import pickle
from typing import Optional, Dict, List, Tuple
from pathlib import Path
import numpy as np
from datetime import datetime

try:
    from sklearn.gaussian_process import GaussianProcessRegressor
    from sklearn.gaussian_process.kernels import RBF, Matern, WhiteKernel, ConstantKernel as C
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    logging.warning("scikit-learn not available - WFLOW-ML disabled")

# Database imports
import sys
sys.path.append('/Users/test/jalsarovar')

try:
    from app import db
    from app.models import Sample, TestResult, ContaminationAnalysis, Location
    HAS_DB = True
except ImportError:
    HAS_DB = False
    logging.warning("Database models not available - using mock data")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WFLOWMLPredictor:
    """
    Gaussian Process predictor for water quality parameters
    """

    def __init__(
        self,
        parameter: str = 'ph_value',
        kernel_type: str = 'rbf_matern',
        length_scale: float = 1.0,
        model_dir: str = '/Users/test/jalsarovar/models'
    ):
        """
        Initialize WFLOW-ML predictor

        Args:
            parameter: Water quality parameter to predict (e.g., 'ph_value', 'tds_ppm')
            kernel_type: Kernel type ('rbf', 'matern', 'rbf_matern')
            length_scale: Initial length scale for kernel
            model_dir: Directory to save/load trained models
        """
        self.parameter = parameter
        self.kernel_type = kernel_type
        self.length_scale = length_scale
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)

        # Initialize model components
        self.gp_model = None
        self.scaler_X = StandardScaler()
        self.scaler_y = StandardScaler()
        self.feature_names = None
        self.trained = False

        # Initialize kernel
        self.kernel = self._create_kernel()

        logger.info(f"Initialized WFLOW-ML for {parameter} with {kernel_type} kernel")

    def _create_kernel(self):
        """
        Create GP kernel based on kernel_type

        Returns:
            Kernel object
        """
        if not HAS_SKLEARN:
            return None

        if self.kernel_type == 'rbf':
            # Radial Basis Function (smooth, infinitely differentiable)
            kernel = C(1.0, (1e-3, 1e3)) * RBF(
                length_scale=self.length_scale,
                length_scale_bounds=(1e-2, 1e2)
            )

        elif self.kernel_type == 'matern':
            # Matérn kernel (more flexible, controls smoothness)
            kernel = C(1.0, (1e-3, 1e3)) * Matern(
                length_scale=self.length_scale,
                length_scale_bounds=(1e-2, 1e2),
                nu=1.5  # Smoothness parameter
            )

        elif self.kernel_type == 'rbf_matern':
            # Hybrid: RBF for spatial + Matérn for temporal
            kernel = (
                C(1.0, (1e-3, 1e3)) * RBF(length_scale=1.0, length_scale_bounds=(1e-2, 1e2)) +
                C(1.0, (1e-3, 1e3)) * Matern(length_scale=1.0, length_scale_bounds=(1e-2, 1e2), nu=1.5)
            )

        else:
            # Default to RBF
            kernel = C(1.0) * RBF(length_scale=1.0)

        # Add white noise kernel for robustness
        kernel += WhiteKernel(noise_level=1e-5, noise_level_bounds=(1e-10, 1e-1))

        return kernel

    def prepare_features(self, samples: List[Dict]) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare feature matrix X and target vector y from samples

        Features:
        - latitude (spatial)
        - longitude (spatial)
        - month (temporal - seasonal variation)
        - distance_to_pollution_source (environmental - if available)
        - elevation (geographical - if available)

        Args:
            samples: List of sample dictionaries with location and parameter data

        Returns:
            (X, y) feature matrix and target vector
        """
        X_list = []
        y_list = []

        for sample in samples:
            # Skip samples without the target parameter
            if self.parameter not in sample or sample[self.parameter] is None:
                continue

            # Extract features
            features = []

            # Spatial features
            features.append(sample.get('latitude', 0.0))
            features.append(sample.get('longitude', 0.0))

            # Temporal feature (month of year, 1-12)
            if 'collection_date' in sample:
                if isinstance(sample['collection_date'], str):
                    date = datetime.fromisoformat(sample['collection_date'])
                else:
                    date = sample['collection_date']
                month = date.month
            else:
                month = 6  # Default to mid-year if date missing

            features.append(month)

            # Environmental features (optional)
            features.append(sample.get('distance_to_source', 0.0))
            features.append(sample.get('elevation', 0.0))

            # Add to lists
            X_list.append(features)
            y_list.append(sample[self.parameter])

        # Convert to numpy arrays
        X = np.array(X_list)
        y = np.array(y_list).reshape(-1, 1)

        # Store feature names
        self.feature_names = [
            'latitude',
            'longitude',
            'month',
            'distance_to_source',
            'elevation'
        ]

        logger.info(f"Prepared {len(X)} samples with {X.shape[1]} features")
        return X, y

    def train(self, samples: List[Dict], n_restarts: int = 10) -> Dict:
        """
        Train Gaussian Process model on sample data

        Args:
            samples: List of sample dictionaries
            n_restarts: Number of restarts for optimizer (higher = better but slower)

        Returns:
            Training statistics dictionary
        """
        if not HAS_SKLEARN:
            logger.error("scikit-learn not available")
            return None

        logger.info(f"Training WFLOW-ML for {self.parameter} on {len(samples)} samples...")

        # Prepare features
        X, y = self.prepare_features(samples)

        if len(X) == 0:
            logger.error(f"No valid samples found for {self.parameter}")
            return None

        # Split into train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        # Standardize features
        X_train_scaled = self.scaler_X.fit_transform(X_train)
        X_test_scaled = self.scaler_X.transform(X_test)

        # Standardize targets
        y_train_scaled = self.scaler_y.fit_transform(y_train)
        y_test_scaled = self.scaler_y.transform(y_test)

        # Create and train GP model
        self.gp_model = GaussianProcessRegressor(
            kernel=self.kernel,
            n_restarts_optimizer=n_restarts,
            normalize_y=False,  # We already normalized
            alpha=1e-10,  # Regularization
            random_state=42
        )

        # Fit model
        logger.info("Fitting Gaussian Process...")
        self.gp_model.fit(X_train_scaled, y_train_scaled.ravel())

        # Evaluate on test set
        y_pred_scaled, y_std_scaled = self.gp_model.predict(X_test_scaled, return_std=True)

        # Inverse transform predictions
        y_pred = self.scaler_y.inverse_transform(y_pred_scaled.reshape(-1, 1)).ravel()
        y_test_actual = self.scaler_y.inverse_transform(y_test_scaled).ravel()

        # Calculate metrics
        mae = np.mean(np.abs(y_pred - y_test_actual))
        rmse = np.sqrt(np.mean((y_pred - y_test_actual) ** 2))
        r2 = 1 - (np.sum((y_test_actual - y_pred) ** 2) / np.sum((y_test_actual - y_test_actual.mean()) ** 2))

        # Log-likelihood score
        log_likelihood = self.gp_model.log_marginal_likelihood()

        stats = {
            'parameter': self.parameter,
            'n_train': len(X_train),
            'n_test': len(X_test),
            'mae': round(mae, 4),
            'rmse': round(rmse, 4),
            'r2_score': round(r2, 4),
            'log_likelihood': round(log_likelihood, 2),
            'kernel': str(self.gp_model.kernel_),
        }

        self.trained = True

        logger.info(f"Training complete: MAE={mae:.4f}, RMSE={rmse:.4f}, R²={r2:.4f}")
        return stats

    def predict(
        self,
        latitude: float,
        longitude: float,
        month: int = None,
        distance_to_source: float = 0.0,
        elevation: float = 0.0,
        return_std: bool = True
    ) -> Tuple[float, float]:
        """
        Predict parameter value at a location

        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            month: Month of year (1-12), uses current month if None
            distance_to_source: Distance to pollution source (km)
            elevation: Elevation (meters)
            return_std: Return uncertainty (standard deviation)

        Returns:
            (predicted_value, uncertainty) if return_std=True, else predicted_value
        """
        if not self.trained or self.gp_model is None:
            logger.error("Model not trained yet")
            return None

        # Use current month if not provided
        if month is None:
            month = datetime.now().month

        # Prepare features
        X = np.array([[latitude, longitude, month, distance_to_source, elevation]])

        # Standardize
        X_scaled = self.scaler_X.transform(X)

        # Predict
        if return_std:
            y_pred_scaled, y_std_scaled = self.gp_model.predict(X_scaled, return_std=True)

            # Inverse transform
            y_pred = self.scaler_y.inverse_transform(y_pred_scaled.reshape(-1, 1)).ravel()[0]

            # Scale uncertainty back (approximate)
            y_std = y_std_scaled[0] * self.scaler_y.scale_[0]

            return (round(y_pred, 4), round(y_std, 4))
        else:
            y_pred_scaled = self.gp_model.predict(X_scaled)
            y_pred = self.scaler_y.inverse_transform(y_pred_scaled.reshape(-1, 1)).ravel()[0]
            return round(y_pred, 4)

    def predict_batch(
        self,
        locations: List[Tuple[float, float]],
        month: int = None
    ) -> List[Dict]:
        """
        Predict parameter values for multiple locations

        Args:
            locations: List of (latitude, longitude) tuples
            month: Month of year (1-12)

        Returns:
            List of prediction dictionaries
        """
        results = []

        for lat, lon in locations:
            pred, std = self.predict(lat, lon, month=month, return_std=True)

            if pred is not None:
                results.append({
                    'latitude': lat,
                    'longitude': lon,
                    'predicted_value': pred,
                    'uncertainty': std,
                    'parameter': self.parameter,
                })

        return results

    def find_high_uncertainty_locations(
        self,
        candidate_locations: List[Tuple[float, float]],
        top_k: int = 10,
        month: int = None
    ) -> List[Dict]:
        """
        Find locations with highest prediction uncertainty (for active learning)

        Args:
            candidate_locations: List of (lat, lon) candidates
            top_k: Number of top uncertain locations to return
            month: Month of year

        Returns:
            List of high-uncertainty locations sorted by uncertainty
        """
        predictions = self.predict_batch(candidate_locations, month=month)

        # Sort by uncertainty (descending)
        predictions.sort(key=lambda x: x['uncertainty'], reverse=True)

        # Return top-k
        return predictions[:top_k]

    def save_model(self, filename: Optional[str] = None):
        """
        Save trained model to disk

        Args:
            filename: Custom filename (optional)
        """
        if not self.trained:
            logger.warning("Model not trained yet - nothing to save")
            return

        if filename is None:
            filename = f"wflow_ml_{self.parameter}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"

        filepath = self.model_dir / filename

        model_data = {
            'gp_model': self.gp_model,
            'scaler_X': self.scaler_X,
            'scaler_y': self.scaler_y,
            'feature_names': self.feature_names,
            'parameter': self.parameter,
            'kernel_type': self.kernel_type,
        }

        with open(filepath, 'wb') as f:
            pickle.dump(model_data, f)

        logger.info(f"Model saved to {filepath}")

    def load_model(self, filename: str):
        """
        Load trained model from disk

        Args:
            filename: Model filename
        """
        filepath = self.model_dir / filename

        if not filepath.exists():
            logger.error(f"Model file not found: {filepath}")
            return False

        with open(filepath, 'rb') as f:
            model_data = pickle.load(f)

        self.gp_model = model_data['gp_model']
        self.scaler_X = model_data['scaler_X']
        self.scaler_y = model_data['scaler_y']
        self.feature_names = model_data['feature_names']
        self.parameter = model_data['parameter']
        self.kernel_type = model_data['kernel_type']
        self.trained = True

        logger.info(f"Model loaded from {filepath}")
        return True


def fetch_training_data_from_db(parameter: str, limit: int = 10000) -> List[Dict]:
    """
    Fetch training data from database

    Args:
        parameter: Parameter name (e.g., 'ph_value', 'tds_ppm')
        limit: Maximum number of samples to fetch

    Returns:
        List of sample dictionaries
    """
    if not HAS_DB:
        logger.warning("Database not available - generating mock data")
        return generate_mock_data(parameter, n_samples=1000)

    try:
        # Query samples with test results and location data
        query = db.session.query(
            Sample.sample_id,
            Sample.collection_date,
            TestResult.ph_value,
            TestResult.temperature_celsius,
            TestResult.tds_ppm,
            TestResult.turbidity_ntu,
            TestResult.conductivity_us_cm,
            TestResult.dissolved_oxygen_mg_l,
            Location.latitude,
            Location.longitude,
            Location.elevation_meters,
        ).join(
            TestResult, Sample.sample_id == TestResult.sample_id
        ).join(
            Location, Sample.location_id == Location.location_id
        ).filter(
            getattr(TestResult, parameter).isnot(None)  # Only samples with this parameter
        ).limit(limit).all()

        # Convert to list of dictionaries
        samples = []
        for row in query:
            sample = {
                'sample_id': row.sample_id,
                'collection_date': row.collection_date,
                'ph_value': row.ph_value,
                'temperature_celsius': row.temperature_celsius,
                'tds_ppm': row.tds_ppm,
                'turbidity_ntu': row.turbidity_ntu,
                'conductivity_us_cm': row.conductivity_us_cm,
                'dissolved_oxygen_mg_l': row.dissolved_oxygen_mg_l,
                'latitude': row.latitude,
                'longitude': row.longitude,
                'elevation': row.elevation_meters or 0.0,
                'distance_to_source': 0.0,  # TODO: Calculate from GIS data
            }
            samples.append(sample)

        logger.info(f"Fetched {len(samples)} samples from database")
        return samples

    except Exception as e:
        logger.error(f"Database query failed: {e}")
        return []


def generate_mock_data(parameter: str, n_samples: int = 1000) -> List[Dict]:
    """
    Generate mock training data for testing

    Args:
        parameter: Parameter name
        n_samples: Number of samples to generate

    Returns:
        List of mock sample dictionaries
    """
    np.random.seed(42)

    samples = []
    for i in range(n_samples):
        # Random location in India (roughly)
        lat = np.random.uniform(8.0, 35.0)
        lon = np.random.uniform(68.0, 97.0)
        month = np.random.randint(1, 13)

        # Generate parameter value based on location and season
        # (Simplified - add spatial and temporal correlations)
        if parameter == 'ph_value':
            base_value = 7.2
            spatial_var = np.sin(lat / 10) * 0.5 + np.cos(lon / 10) * 0.3
            temporal_var = np.sin(month / 12 * 2 * np.pi) * 0.4  # Seasonal
            noise = np.random.normal(0, 0.2)
            value = base_value + spatial_var + temporal_var + noise

        elif parameter == 'tds_ppm':
            base_value = 300
            spatial_var = np.sin(lat / 5) * 100 + np.cos(lon / 5) * 80
            temporal_var = np.sin(month / 12 * 2 * np.pi) * 50
            noise = np.random.normal(0, 30)
            value = base_value + spatial_var + temporal_var + noise

        else:
            value = np.random.uniform(0, 100)

        sample = {
            'sample_id': f'MOCK{i:06d}',
            'collection_date': datetime(2024, month, 15),
            'latitude': lat,
            'longitude': lon,
            'elevation': np.random.uniform(0, 2000),
            'distance_to_source': np.random.uniform(0, 50),
            parameter: value,
        }
        samples.append(sample)

    return samples


# Example usage
if __name__ == '__main__':
    print("=" * 60)
    print("WFLOW-ML: Gaussian Process Water Quality Prediction")
    print("=" * 60)

    if not HAS_SKLEARN:
        print("\nscikit-learn not available - install with: pip install scikit-learn")
        exit(1)

    # Initialize predictor for pH
    predictor = WFLOWMLPredictor(
        parameter='ph_value',
        kernel_type='rbf_matern'
    )

    # Fetch training data
    print("\nFetching training data...")
    training_data = fetch_training_data_from_db('ph_value', limit=5000)

    if len(training_data) == 0:
        print("No training data available")
        exit(1)

    # Train model
    print("\nTraining model...")
    stats = predictor.train(training_data, n_restarts=10)

    if stats:
        print("\nTraining Statistics:")
        print(f"  Parameter: {stats['parameter']}")
        print(f"  Training samples: {stats['n_train']}")
        print(f"  Test samples: {stats['n_test']}")
        print(f"  MAE: {stats['mae']:.4f}")
        print(f"  RMSE: {stats['rmse']:.4f}")
        print(f"  R² Score: {stats['r2_score']:.4f}")
        print(f"  Log-Likelihood: {stats['log_likelihood']:.2f}")

    # Make predictions
    print("\n" + "-" * 60)
    print("Making predictions...")

    test_locations = [
        (28.6139, 77.2090, "Delhi"),
        (19.0760, 72.8777, "Mumbai"),
        (13.0827, 80.2707, "Chennai"),
        (22.5726, 88.3639, "Kolkata"),
    ]

    for lat, lon, city in test_locations:
        pred, uncertainty = predictor.predict(lat, lon, month=6, return_std=True)
        print(f"\n{city} (Lat: {lat}, Lon: {lon}):")
        print(f"  Predicted pH: {pred:.2f} ± {uncertainty:.2f}")

    # Find high-uncertainty locations
    print("\n" + "-" * 60)
    print("Finding high-uncertainty locations for active learning...")

    candidate_locations = [
        (lat, lon) for lat in np.linspace(20, 30, 20)
        for lon in np.linspace(70, 85, 20)
    ]

    high_uncertainty = predictor.find_high_uncertainty_locations(
        candidate_locations, top_k=5, month=6
    )

    print(f"\nTop 5 locations with highest uncertainty:")
    for i, loc in enumerate(high_uncertainty, 1):
        print(f"{i}. Lat: {loc['latitude']:.2f}, Lon: {loc['longitude']:.2f}")
        print(f"   Predicted: {loc['predicted_value']:.2f} ± {loc['uncertainty']:.2f}")

    # Save model
    print("\n" + "-" * 60)
    predictor.save_model()

    print("\n" + "=" * 60)
    print("WFLOW-ML test complete")
    print("=" * 60)
