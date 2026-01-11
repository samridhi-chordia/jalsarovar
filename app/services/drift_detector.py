"""
CUSUM Drift Detection Service
Implements Cumulative Sum (CUSUM) change point detection for monitoring gradual parameter drift
Complements anomaly detection for comprehensive water quality monitoring (sudden + gradual changes)
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import deque


class CUSUMDriftDetector:
    """
    CUSUM (Cumulative Sum) drift detector for water quality parameters

    Detects gradual changes that may indicate:
    - Pipe corrosion (gradual TDS increase)
    - Membrane degradation (gradual RO performance decline)
    - Seasonal effects (temperature drift)
    - Infrastructure aging (conductivity changes)
    - Source water changes (pH drift)

    Unlike spike detection (sudden anomalies), CUSUM detects GRADUAL drift
    """

    def __init__(self, threshold=5.0, drift_magnitude=0.5, window_size=100):
        """
        Initialize CUSUM drift detector

        Parameters:
        -----------
        threshold : float (default=5.0)
            Detection threshold (H parameter in CUSUM)
            Higher = less sensitive to small drifts
        drift_magnitude : float (default=0.5)
            Minimum drift size to detect (K parameter in CUSUM)
            In units of standard deviations
        window_size : int (default=100)
            Number of recent measurements to consider for baseline
        """
        self.threshold = threshold
        self.drift_magnitude = drift_magnitude
        self.window_size = window_size

        # Track CUSUM statistics for each parameter
        self.cusum_stats = {}

        # Parameters to monitor (common water quality parameters)
        self.monitored_parameters = [
            'ph_value', 'tds_ppm', 'temperature_celsius', 'turbidity_ntu',
            'conductivity_us_cm', 'free_chlorine_mg_l', 'total_coliform_mpn',
            'iron_mg_l', 'chloride_mg_l', 'ammonia_mg_l'
        ]

        # Initialize statistics
        self._reset_stats()

    def _reset_stats(self):
        """Reset CUSUM statistics for all parameters"""
        for param in self.monitored_parameters:
            self.cusum_stats[param] = {
                'upper_cusum': 0.0,  # Detects upward drift
                'lower_cusum': 0.0,  # Detects downward drift
                'mean': None,
                'std': None,
                'recent_values': deque(maxlen=self.window_size),
                'drift_detected': False,
                'drift_direction': None,  # 'upward' or 'downward'
                'drift_start_time': None,
                'drift_magnitude_sigma': 0.0
            }

    def update(self, measurement: Dict, measurement_time: Optional[datetime] = None) -> Dict[str, Dict]:
        """
        Update CUSUM statistics with new measurement and check for drift

        Parameters:
        -----------
        measurement : Dict
            Water quality measurement with parameters
        measurement_time : datetime (optional)
            Timestamp of measurement (defaults to current time)

        Returns:
        --------
        Dict[str, Dict] : Drift detection results for each parameter
            {
                'parameter_name': {
                    'drift_detected': bool,
                    'drift_direction': str,  # 'upward', 'downward', or None
                    'drift_magnitude_sigma': float,  # How many std devs from baseline
                    'cusum_value': float,
                    'threshold': float
                }
            }
        """
        if measurement_time is None:
            measurement_time = datetime.now()

        results = {}

        for param in self.monitored_parameters:
            if param not in measurement or measurement[param] is None:
                results[param] = {
                    'drift_detected': False,
                    'drift_direction': None,
                    'drift_magnitude_sigma': 0.0,
                    'cusum_value': 0.0,
                    'threshold': self.threshold
                }
                continue

            value = float(measurement[param])
            stats = self.cusum_stats[param]

            # Add to recent values
            stats['recent_values'].append(value)

            # Calculate or update baseline statistics
            if len(stats['recent_values']) >= 30:  # Need at least 30 samples
                stats['mean'] = np.mean(stats['recent_values'])
                stats['std'] = np.std(stats['recent_values'])

                if stats['std'] > 0:
                    # Calculate normalized deviation
                    deviation = (value - stats['mean']) / stats['std']

                    # Update CUSUM statistics
                    # Upper CUSUM (detects upward drift)
                    stats['upper_cusum'] = max(0, stats['upper_cusum'] + deviation - self.drift_magnitude)

                    # Lower CUSUM (detects downward drift)
                    stats['lower_cusum'] = max(0, stats['lower_cusum'] - deviation - self.drift_magnitude)

                    # Check for drift
                    drift_detected = False
                    drift_direction = None
                    cusum_value = 0.0

                    if stats['upper_cusum'] > self.threshold:
                        drift_detected = True
                        drift_direction = 'upward'
                        cusum_value = stats['upper_cusum']

                        if not stats['drift_detected']:
                            stats['drift_start_time'] = measurement_time

                    elif stats['lower_cusum'] > self.threshold:
                        drift_detected = True
                        drift_direction = 'downward'
                        cusum_value = stats['lower_cusum']

                        if not stats['drift_detected']:
                            stats['drift_start_time'] = measurement_time

                    # Update drift status
                    stats['drift_detected'] = drift_detected
                    stats['drift_direction'] = drift_direction
                    stats['drift_magnitude_sigma'] = abs(deviation) if drift_detected else 0.0

                    # Store results
                    results[param] = {
                        'drift_detected': drift_detected,
                        'drift_direction': drift_direction,
                        'drift_magnitude_sigma': stats['drift_magnitude_sigma'],
                        'cusum_value': max(stats['upper_cusum'], stats['lower_cusum']),
                        'threshold': self.threshold,
                        'current_value': value,
                        'baseline_mean': stats['mean'],
                        'baseline_std': stats['std']
                    }

                    # If drift resolved, reset CUSUMs
                    if not drift_detected and (stats['upper_cusum'] < 1.0 and stats['lower_cusum'] < 1.0):
                        stats['upper_cusum'] = 0.0
                        stats['lower_cusum'] = 0.0
                        stats['drift_start_time'] = None
                else:
                    # Standard deviation is zero (constant values)
                    results[param] = {
                        'drift_detected': False,
                        'drift_direction': None,
                        'drift_magnitude_sigma': 0.0,
                        'cusum_value': 0.0,
                        'threshold': self.threshold
                    }
            else:
                # Not enough data yet
                results[param] = {
                    'drift_detected': False,
                    'drift_direction': None,
                    'drift_magnitude_sigma': 0.0,
                    'cusum_value': 0.0,
                    'threshold': self.threshold,
                    'message': f'Insufficient data ({len(stats["recent_values"])}/30)'
                }

        return results

    def batch_detect(self, measurements: List[Dict], timestamps: Optional[List[datetime]] = None) -> pd.DataFrame:
        """
        Detect drift in a batch of measurements (time-series)

        Parameters:
        -----------
        measurements : List[Dict]
            Time-ordered water quality measurements
        timestamps : List[datetime] (optional)
            Timestamps for each measurement

        Returns:
        --------
        pd.DataFrame : Drift detection results over time
        """
        if timestamps is None:
            timestamps = [datetime.now() - timedelta(hours=i) for i in range(len(measurements)-1, -1, -1)]

        # Reset statistics for clean batch processing
        self._reset_stats()

        results_list = []

        for measurement, timestamp in zip(measurements, timestamps):
            drift_results = self.update(measurement, timestamp)

            # Flatten results for dataframe
            row = {'timestamp': timestamp}
            for param, result in drift_results.items():
                row[f'{param}_drift_detected'] = result['drift_detected']
                row[f'{param}_drift_direction'] = result['drift_direction']
                row[f'{param}_cusum'] = result['cusum_value']

            results_list.append(row)

        return pd.DataFrame(results_list)

    def get_drift_summary(self) -> Dict:
        """
        Get summary of current drift status for all parameters

        Returns:
        --------
        Dict : Summary of drift status
        """
        summary = {
            'parameters_with_drift': [],
            'drift_details': {}
        }

        for param, stats in self.cusum_stats.items():
            if stats['drift_detected']:
                summary['parameters_with_drift'].append(param)
                summary['drift_details'][param] = {
                    'direction': stats['drift_direction'],
                    'magnitude_sigma': stats['drift_magnitude_sigma'],
                    'start_time': stats['drift_start_time'].isoformat() if stats['drift_start_time'] else None,
                    'duration_hours': (datetime.now() - stats['drift_start_time']).total_seconds() / 3600
                                      if stats['drift_start_time'] else 0,
                    'cusum_value': max(stats['upper_cusum'], stats['lower_cusum'])
                }

        summary['n_parameters_drifting'] = len(summary['parameters_with_drift'])
        summary['overall_status'] = 'drift_detected' if summary['parameters_with_drift'] else 'stable'

        return summary

    def reset_parameter(self, parameter: str):
        """
        Reset CUSUM statistics for a specific parameter
        (e.g., after maintenance or recalibration)

        Parameters:
        -----------
        parameter : str
            Parameter name to reset
        """
        if parameter in self.cusum_stats:
            self.cusum_stats[parameter] = {
                'upper_cusum': 0.0,
                'lower_cusum': 0.0,
                'mean': None,
                'std': None,
                'recent_values': deque(maxlen=self.window_size),
                'drift_detected': False,
                'drift_direction': None,
                'drift_start_time': None,
                'drift_magnitude_sigma': 0.0
            }

    def reset_all(self):
        """Reset all CUSUM statistics"""
        self._reset_stats()

    def get_stats(self) -> Dict:
        """
        Get current statistics for all parameters

        Returns:
        --------
        Dict : Current statistics
        """
        stats_summary = {}

        for param, stats in self.cusum_stats.items():
            stats_summary[param] = {
                'n_samples': len(stats['recent_values']),
                'baseline_mean': stats['mean'],
                'baseline_std': stats['std'],
                'upper_cusum': stats['upper_cusum'],
                'lower_cusum': stats['lower_cusum'],
                'drift_detected': stats['drift_detected'],
                'drift_direction': stats['drift_direction']
            }

        return stats_summary


# Singleton instance
_drift_detector_instance = None


def get_drift_detector() -> CUSUMDriftDetector:
    """
    Get or create singleton CUSUM drift detector instance

    Returns:
    --------
    CUSUMDriftDetector : Drift detector instance
    """
    global _drift_detector_instance

    if _drift_detector_instance is None:
        _drift_detector_instance = CUSUMDriftDetector()

    return _drift_detector_instance
