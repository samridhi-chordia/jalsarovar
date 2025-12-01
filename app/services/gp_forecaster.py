"""
Gaussian Process Water Quality Forecaster
90-day forecasting horizon with uncertainty quantification for early warning system
Research paper requirement: GP-based prediction with quantified uncertainty
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel, ConstantKernel as C
from sklearn.preprocessing import StandardScaler
import joblib


class GaussianProcessForecaster:
    """
    Gaussian Process forecaster for water quality parameters

    Features:
    - 90-day forecast horizon (research paper requirement)
    - Uncertainty quantification (mean ± std)
    - 14-day early warning threshold
    - Multi-parameter forecasting (pH, TDS, turbidity, etc.)
    - Automatic kernel selection
    """

    def __init__(self, parameter: str = 'ph_value', forecast_days: int = 90):
        """
        Initialize GP forecaster

        Parameters:
        -----------
        parameter : str
            Water quality parameter to forecast
            Options: 'ph_value', 'tds_ppm', 'turbidity_ntu', 'temperature_celsius'
        forecast_days : int
            Forecast horizon in days (default: 90)
        """
        self.parameter = parameter
        self.forecast_days = forecast_days
        self.early_warning_days = 14  # Early warning threshold

        # Kernel: RBF (captures smoothness) + White Noise (measurement error)
        # C(constant) * RBF(length_scale) + WhiteKernel(noise)
        kernel = C(1.0, (1e-3, 1e3)) * RBF(length_scale=10.0, length_scale_bounds=(1.0, 100.0)) + \
                 WhiteKernel(noise_level=0.1, noise_level_bounds=(1e-5, 1.0))

        self.model = GaussianProcessRegressor(
            kernel=kernel,
            n_restarts_optimizer=10,  # Multiple kernel hyperparameter optimization runs
            alpha=1e-10,  # Regularization
            normalize_y=True,  # Normalize target values
            random_state=42
        )

        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_names = []

    def prepare_features(self, measurements: List[Dict], timestamps: List[datetime]) -> pd.DataFrame:
        """
        Prepare time-series features from historical measurements

        Parameters:
        -----------
        measurements : List[Dict]
            Historical water quality measurements
        timestamps : List[datetime]
            Timestamps for each measurement

        Returns:
        --------
        pd.DataFrame : Feature matrix with temporal and lag features
        """
        df = pd.DataFrame(measurements)
        df['timestamp'] = pd.to_datetime(timestamps)
        df = df.sort_values('timestamp').reset_index(drop=True)

        # Extract parameter values
        if self.parameter not in df.columns:
            raise ValueError(f"Parameter '{self.parameter}' not found in measurements")

        # Create temporal features
        df['days_since_start'] = (df['timestamp'] - df['timestamp'].min()).dt.total_seconds() / (24 * 3600)
        df['day_of_year'] = df['timestamp'].dt.dayofyear
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['month'] = df['timestamp'].dt.month

        # Cyclical encoding for seasonality
        df['day_of_year_sin'] = np.sin(2 * np.pi * df['day_of_year'] / 365.25)
        df['day_of_year_cos'] = np.cos(2 * np.pi * df['day_of_year'] / 365.25)
        df['day_of_week_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
        df['day_of_week_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)

        # Lag features (past values)
        for lag in [1, 3, 7, 14, 30]:
            df[f'{self.parameter}_lag_{lag}'] = df[self.parameter].shift(lag)

        # Rolling statistics (trend and variability)
        for window in [7, 14, 30]:
            df[f'{self.parameter}_roll_mean_{window}'] = df[self.parameter].rolling(window, min_periods=1).mean()
            df[f'{self.parameter}_roll_std_{window}'] = df[self.parameter].rolling(window, min_periods=1).std()
            df[f'{self.parameter}_roll_min_{window}'] = df[self.parameter].rolling(window, min_periods=1).min()
            df[f'{self.parameter}_roll_max_{window}'] = df[self.parameter].rolling(window, min_periods=1).max()

        # Fill NaN values (from lag/rolling features)
        df = df.bfill().ffill().fillna(0)

        return df

    def train(self, measurements: List[Dict], timestamps: List[datetime]) -> Dict:
        """
        Train Gaussian Process on historical data

        Parameters:
        -----------
        measurements : List[Dict]
            Historical water quality measurements
        timestamps : List[datetime]
            Timestamps for each measurement

        Returns:
        --------
        Dict : Training metrics
        """
        # Prepare features
        df = self.prepare_features(measurements, timestamps)

        # Select feature columns
        feature_cols = [
            'days_since_start', 'day_of_year_sin', 'day_of_year_cos',
            'day_of_week_sin', 'day_of_week_cos'
        ]

        # Add lag and rolling features
        lag_cols = [col for col in df.columns if 'lag' in col or 'roll' in col]
        feature_cols.extend(lag_cols)

        self.feature_names = feature_cols

        X = df[feature_cols].values
        y = df[self.parameter].values

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Train GP
        print(f"Training Gaussian Process for {self.parameter}...")
        print(f"  Training samples: {len(X)}")
        print(f"  Features: {len(feature_cols)}")

        self.model.fit(X_scaled, y)
        self.is_trained = True

        # Store training data info for forecasting
        self.last_timestamp = df['timestamp'].max()
        self.days_since_start_offset = df['days_since_start'].max()
        self.last_measurements = df.tail(30)  # Keep last 30 days for lag features

        # Training metrics
        y_pred, y_std = self.model.predict(X_scaled, return_std=True)
        rmse = np.sqrt(np.mean((y - y_pred) ** 2))
        mae = np.mean(np.abs(y - y_pred))

        # Log marginal likelihood (model evidence)
        log_likelihood = self.model.log_marginal_likelihood()

        metrics = {
            'parameter': self.parameter,
            'n_samples': len(X),
            'n_features': len(feature_cols),
            'rmse': float(rmse),
            'mae': float(mae),
            'log_likelihood': float(log_likelihood),
            'kernel': str(self.model.kernel_),
            'mean_uncertainty': float(np.mean(y_std))
        }

        print(f"✓ GP trained successfully!")
        print(f"  RMSE: {rmse:.4f}")
        print(f"  MAE: {mae:.4f}")
        print(f"  Mean uncertainty (σ): {np.mean(y_std):.4f}")
        print(f"  Log likelihood: {log_likelihood:.2f}")
        print(f"  Optimized kernel: {self.model.kernel_}")

        return metrics

    def forecast(self, days_ahead: Optional[int] = None) -> pd.DataFrame:
        """
        Generate forecast for future days with uncertainty

        Parameters:
        -----------
        days_ahead : int (optional)
            Number of days to forecast (default: self.forecast_days)

        Returns:
        --------
        pd.DataFrame : Forecast with columns:
            - timestamp: Future dates
            - mean: Predicted mean value
            - std: Uncertainty (standard deviation)
            - lower_95ci: Lower 95% confidence interval
            - upper_95ci: Upper 95% confidence interval
            - early_warning: Boolean flag for values outside safe range
        """
        if not self.is_trained:
            raise RuntimeError("Model not trained. Call train() first.")

        if days_ahead is None:
            days_ahead = self.forecast_days

        # Generate future timestamps
        future_timestamps = [self.last_timestamp + timedelta(days=i+1) for i in range(days_ahead)]

        # Create future feature matrix
        future_features = []

        for i, future_ts in enumerate(future_timestamps):
            days_since_start = self.days_since_start_offset + i + 1
            day_of_year = future_ts.timetuple().tm_yday
            day_of_week = future_ts.weekday()

            # Temporal features
            features = {
                'days_since_start': days_since_start,
                'day_of_year_sin': np.sin(2 * np.pi * day_of_year / 365.25),
                'day_of_year_cos': np.cos(2 * np.pi * day_of_year / 365.25),
                'day_of_week_sin': np.sin(2 * np.pi * day_of_week / 7),
                'day_of_week_cos': np.cos(2 * np.pi * day_of_week / 7),
            }

            # Lag features (use last known values or previous predictions)
            # For simplicity, use recent historical averages
            recent_mean = self.last_measurements[self.parameter].mean()
            recent_std = self.last_measurements[self.parameter].std()
            recent_min = self.last_measurements[self.parameter].min()
            recent_max = self.last_measurements[self.parameter].max()

            for lag in [1, 3, 7, 14, 30]:
                features[f'{self.parameter}_lag_{lag}'] = recent_mean

            for window in [7, 14, 30]:
                features[f'{self.parameter}_roll_mean_{window}'] = recent_mean
                features[f'{self.parameter}_roll_std_{window}'] = recent_std
                features[f'{self.parameter}_roll_min_{window}'] = recent_min
                features[f'{self.parameter}_roll_max_{window}'] = recent_max

            future_features.append(features)

        # Convert to DataFrame
        future_df = pd.DataFrame(future_features)
        X_future = future_df[self.feature_names].values
        X_future_scaled = self.scaler.transform(X_future)

        # Predict with uncertainty
        y_mean, y_std = self.model.predict(X_future_scaled, return_std=True)

        # Create forecast DataFrame
        forecast_df = pd.DataFrame({
            'timestamp': future_timestamps,
            'mean': y_mean,
            'std': y_std,
            'lower_95ci': y_mean - 1.96 * y_std,  # 95% confidence interval
            'upper_95ci': y_mean + 1.96 * y_std
        })

        # Early warning system (parameter-specific thresholds)
        forecast_df['early_warning'] = self._check_early_warning(forecast_df)

        return forecast_df

    def _check_early_warning(self, forecast_df: pd.DataFrame) -> np.ndarray:
        """
        Check if forecast values trigger early warning

        Uses WHO/BIS water quality standards:
        - pH: 6.5-8.5 (safe range)
        - TDS: <500 ppm (acceptable), <1000 ppm (permissible)
        - Turbidity: <1 NTU (excellent), <5 NTU (acceptable)
        - Temperature: 15-30°C (normal range)
        """
        # Define safe ranges per parameter
        safe_ranges = {
            'ph_value': (6.5, 8.5),
            'tds_ppm': (0, 500),
            'turbidity_ntu': (0, 5),
            'temperature_celsius': (15, 30),
            'conductivity_us_cm': (0, 800),
            'free_chlorine_mg_l': (0.2, 1.0)
        }

        if self.parameter not in safe_ranges:
            # Unknown parameter, no early warning
            return np.zeros(len(forecast_df), dtype=bool)

        min_safe, max_safe = safe_ranges[self.parameter]

        # Warning if predicted mean is outside safe range
        warnings = (forecast_df['mean'] < min_safe) | (forecast_df['mean'] > max_safe)

        # Also warn if 95% CI lower bound exceeds threshold (high confidence of violation)
        warnings |= (forecast_df['lower_95ci'] > max_safe) | (forecast_df['upper_95ci'] < min_safe)

        return warnings.values

    def get_early_warnings(self, forecast_df: pd.DataFrame) -> List[Dict]:
        """
        Extract early warning alerts from forecast

        Parameters:
        -----------
        forecast_df : pd.DataFrame
            Forecast results from forecast()

        Returns:
        --------
        List[Dict] : Early warning alerts
        """
        warnings = []

        # Check if any warnings in next 14 days
        early_warning_df = forecast_df.head(self.early_warning_days)

        for idx, row in early_warning_df[early_warning_df['early_warning']].iterrows():
            warnings.append({
                'parameter': self.parameter,
                'timestamp': row['timestamp'].isoformat(),
                'days_ahead': idx + 1,
                'predicted_mean': float(row['mean']),
                'uncertainty_std': float(row['std']),
                'lower_95ci': float(row['lower_95ci']),
                'upper_95ci': float(row['upper_95ci']),
                'severity': self._assess_severity(row)
            })

        return warnings

    def _assess_severity(self, forecast_row: pd.Series) -> str:
        """Assess warning severity based on deviation from safe range"""
        safe_ranges = {
            'ph_value': (6.5, 8.5),
            'tds_ppm': (0, 500),
            'turbidity_ntu': (0, 5),
            'temperature_celsius': (15, 30)
        }

        if self.parameter not in safe_ranges:
            return 'unknown'

        min_safe, max_safe = safe_ranges[self.parameter]
        mean_val = forecast_row['mean']

        # Calculate deviation magnitude
        if mean_val < min_safe:
            deviation = (min_safe - mean_val) / min_safe
        elif mean_val > max_safe:
            deviation = (mean_val - max_safe) / max_safe
        else:
            return 'low'

        # Classify severity
        if deviation > 0.5:
            return 'critical'
        elif deviation > 0.3:
            return 'high'
        elif deviation > 0.15:
            return 'medium'
        else:
            return 'low'

    def save(self, filepath: str):
        """Save trained GP model"""
        if not self.is_trained:
            raise RuntimeError("Cannot save untrained model")

        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'parameter': self.parameter,
            'forecast_days': self.forecast_days,
            'feature_names': self.feature_names,
            'last_timestamp': self.last_timestamp,
            'days_since_start_offset': self.days_since_start_offset,
            'last_measurements': self.last_measurements
        }

        joblib.dump(model_data, filepath)
        print(f"✓ GP model saved: {filepath}")

    @classmethod
    def load(cls, filepath: str):
        """Load trained GP model"""
        model_data = joblib.load(filepath)

        forecaster = cls(
            parameter=model_data['parameter'],
            forecast_days=model_data['forecast_days']
        )

        forecaster.model = model_data['model']
        forecaster.scaler = model_data['scaler']
        forecaster.feature_names = model_data['feature_names']
        forecaster.last_timestamp = model_data['last_timestamp']
        forecaster.days_since_start_offset = model_data['days_since_start_offset']
        forecaster.last_measurements = model_data['last_measurements']
        forecaster.is_trained = True

        print(f"✓ GP model loaded: {filepath}")
        return forecaster


# Singleton instances for common parameters
_gp_forecasters = {}

def get_gp_forecaster(parameter: str = 'ph_value', forecast_days: int = 90) -> GaussianProcessForecaster:
    """
    Get or create GP forecaster instance

    Parameters:
    -----------
    parameter : str
        Water quality parameter
    forecast_days : int
        Forecast horizon

    Returns:
    --------
    GaussianProcessForecaster : Forecaster instance
    """
    key = f"{parameter}_{forecast_days}"

    if key not in _gp_forecasters:
        _gp_forecasters[key] = GaussianProcessForecaster(parameter, forecast_days)

    return _gp_forecasters[key]


if __name__ == '__main__':
    # Example usage and testing
    print("Gaussian Process Water Quality Forecaster")
    print("=" * 70)

    # Generate synthetic water quality data (pH)
    np.random.seed(42)
    n_days = 180
    timestamps = [datetime(2024, 1, 1) + timedelta(days=i) for i in range(n_days)]

    # Simulate pH with seasonal variation + noise
    days = np.arange(n_days)
    seasonal = 0.3 * np.sin(2 * np.pi * days / 365.25)  # Annual cycle
    trend = 0.001 * days  # Slight upward trend
    noise = np.random.normal(0, 0.1, n_days)
    ph_values = 7.2 + seasonal + trend + noise

    measurements = [{'ph_value': ph} for ph in ph_values]

    # Create and train forecaster
    forecaster = GaussianProcessForecaster(parameter='ph_value', forecast_days=90)

    print("\nTraining GP on 180 days of historical data...")
    metrics = forecaster.train(measurements, timestamps)

    # Generate 90-day forecast
    print(f"\nGenerating {forecaster.forecast_days}-day forecast...")
    forecast = forecaster.forecast()

    print(f"\nForecast Summary:")
    print(f"  Forecast period: {forecast['timestamp'].min()} to {forecast['timestamp'].max()}")
    print(f"  Mean predicted pH: {forecast['mean'].mean():.2f}")
    print(f"  Mean uncertainty: {forecast['std'].mean():.3f}")
    print(f"  Early warnings: {forecast['early_warning'].sum()} days")

    # Check for early warnings
    warnings = forecaster.get_early_warnings(forecast)

    if warnings:
        print(f"\n⚠ Early Warning Alerts (next 14 days):")
        for warning in warnings:
            print(f"  Day {warning['days_ahead']}: {warning['predicted_mean']:.2f} ± {warning['uncertainty_std']:.2f}")
            print(f"    Severity: {warning['severity']}")
    else:
        print(f"\n✓ No early warnings detected (next 14 days)")

    print(f"\n✓ Gaussian Process forecaster ready for production use!")
