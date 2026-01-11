"""
Trend Analyzer Service
Provides advanced time-series analysis and trend detection for water quality data
Adapted for Jal Sarovar Water Quality Monitoring System
"""
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict

from app import db
from app.models import Site, WaterSample, TestResult, Analysis


class TrendAnalyzer:
    """Analyzes water quality trends over time using statistical methods"""

    def __init__(self):
        """Initialize the trend analyzer"""
        # Key parameters for trend analysis
        self.key_parameters = [
            'turbidity_ntu',
            'ph_value',
            'tds_ppm',
            'free_chlorine_mg_l',
            'total_coliform_mpn',
            'iron_mg_l',
            'chloride_mg_l',
            'temperature_celsius',
            'conductivity_us_cm',
            'ammonia_mg_l'
        ]

        # WHO/BIS standards for quality assessment (IS 10500:2012)
        self.standards = {
            'turbidity_ntu': {'max': 5.0, 'desirable': 1.0},
            'ph_value': {'min': 6.5, 'max': 8.5},
            'tds_ppm': {'max': 500, 'acceptable': 2000},
            'free_chlorine_mg_l': {'min': 0.2, 'max': 1.0},
            'iron_mg_l': {'max': 0.3},
            'chloride_mg_l': {'max': 250, 'acceptable': 1000},
            'temperature_celsius': {'min': 10, 'max': 25},
            'conductivity_us_cm': {'max': 1000},
            'ammonia_mg_l': {'max': 0.5},
            'total_coliform_mpn': {'max': 0}
        }

    def analyze_site_trends(self, site_id: int, days: int = 365) -> Dict[str, Any]:
        """
        Comprehensive trend analysis for a specific site

        Args:
            site_id: Site to analyze
            days: Number of days to look back (default 365)

        Returns:
            Dictionary with trend analysis results
        """
        site = Site.query.get(site_id)
        if not site:
            return {'error': 'Site not found'}

        # Get historical data
        cutoff_date = datetime.now() - timedelta(days=days)
        samples = WaterSample.query.filter(
            WaterSample.site_id == site_id,
            WaterSample.collection_date >= cutoff_date
        ).order_by(WaterSample.collection_date).all()

        if len(samples) < 3:
            return {
                'error': 'Insufficient data',
                'message': f'Need at least 3 samples for trend analysis. Found {len(samples)}.'
            }

        # Build time-series dataset
        time_series_data = self._build_time_series(samples)

        if not time_series_data:
            return {'error': 'No valid test data found'}

        # Analyze trends for each parameter
        parameter_trends = {}
        for param in self.key_parameters:
            if param in time_series_data:
                trend_result = self._analyze_parameter_trend(
                    time_series_data[param],
                    param
                )
                if trend_result:
                    parameter_trends[param] = trend_result

        # Calculate overall site trend
        overall_trend = self._calculate_overall_trend(parameter_trends)

        # Detect change points
        change_points = self._detect_change_points(time_series_data)

        # Calculate early warning score
        warning_score = self._calculate_warning_score(parameter_trends)

        return {
            'site_id': site_id,
            'site_name': site.site_name,
            'analysis_period_days': days,
            'samples_analyzed': len(samples),
            'overall_trend': overall_trend,
            'parameter_trends': parameter_trends,
            'change_points': change_points,
            'warning_score': warning_score,
            'warning_level': self._get_warning_level(warning_score),
            'recommendations': self._generate_recommendations(parameter_trends, warning_score)
        }

    def _build_time_series(self, samples: List[WaterSample]) -> Dict[str, Dict]:
        """Build time-series data from samples"""
        time_series = defaultdict(lambda: {'dates': [], 'values': []})

        for sample in samples:
            # Get test result for this sample
            test_result = TestResult.query.filter_by(sample_id=sample.id).first()
            if not test_result:
                continue

            for param in self.key_parameters:
                value = getattr(test_result, param, None)
                if value is not None:
                    time_series[param]['dates'].append(sample.collection_date)
                    time_series[param]['values'].append(float(value))

        # Convert to format suitable for analysis
        result = {}
        for param, data in time_series.items():
            if len(data['dates']) >= 3:  # Need at least 3 points
                # Convert date to datetime if needed for timestamp()
                timestamps = []
                for d in data['dates']:
                    if hasattr(d, 'timestamp'):
                        timestamps.append(d.timestamp())
                    else:
                        # Convert date to datetime
                        timestamps.append(datetime.combine(d, datetime.min.time()).timestamp())
                result[param] = {
                    'dates': data['dates'],
                    'values': np.array(data['values']),
                    'timestamps': timestamps
                }

        return result

    def _analyze_parameter_trend(self, data: Dict, parameter: str) -> Optional[Dict[str, Any]]:
        """Analyze trend for a single parameter using statistical methods"""
        values = data['values']
        timestamps = np.array(data['timestamps'])
        dates = data['dates']

        if len(values) < 3:
            return None

        # Simple linear regression for trend detection
        try:
            # Calculate trend using numpy polyfit
            coefficients = np.polyfit(timestamps, values, 1)
            slope = coefficients[0]
            intercept = coefficients[1]

            # Calculate R-squared
            predicted = np.polyval(coefficients, timestamps)
            ss_res = np.sum((values - predicted) ** 2)
            ss_tot = np.sum((values - np.mean(values)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

            # Calculate p-value approximation (simplified)
            n = len(values)
            if n > 2 and r_squared < 1:
                t_stat = slope * np.sqrt(n - 2) / np.sqrt(ss_res / (n - 2)) if ss_res > 0 else 0
                # Simplified p-value estimation
                p_value = 0.05 if abs(t_stat) > 2 else 0.1
            else:
                p_value = 1.0

        except Exception:
            slope = 0
            r_squared = 0
            p_value = 1.0

        # Calculate trend classification
        trend_classification = self._classify_trend(slope, p_value, parameter)

        # Calculate change rate (% per month)
        if len(values) > 1:
            time_diff_days = (dates[-1] - dates[0]).days
            value_change = values[-1] - values[0]
            avg_value = np.mean(values)
            if avg_value > 0 and time_diff_days > 0:
                monthly_change_pct = (value_change / avg_value) * (30 / time_diff_days) * 100
            else:
                monthly_change_pct = 0.0
        else:
            monthly_change_pct = 0.0

        # Compliance status
        latest_value = values[-1]
        compliance = self._check_compliance(parameter, latest_value)

        return {
            'parameter': parameter,
            'trend': trend_classification,
            'slope': float(slope),
            'p_value': float(p_value),
            'r_squared': float(r_squared),
            'monthly_change_pct': float(monthly_change_pct),
            'current_value': float(latest_value),
            'mean_value': float(np.mean(values)),
            'std_dev': float(np.std(values)),
            'min_value': float(np.min(values)),
            'max_value': float(np.max(values)),
            'data_points': len(values),
            'first_date': dates[0].isoformat() if hasattr(dates[0], 'isoformat') else str(dates[0]),
            'last_date': dates[-1].isoformat() if hasattr(dates[-1], 'isoformat') else str(dates[-1]),
            'compliance': compliance
        }

    def _classify_trend(self, slope: float, p_value: float, parameter: str) -> str:
        """
        Classify trend as improving, declining, or stable

        For parameters where lower is better (most contaminants),
        negative slope = improving
        For parameters where optimal is in range (pH, chlorine),
        trend toward optimal = improving
        """
        # Not statistically significant
        if p_value > 0.05:
            return 'stable'

        # Check parameter type
        lower_is_better = parameter not in ['ph_value', 'free_chlorine_mg_l']

        if lower_is_better:
            if slope < 0:
                return 'improving'
            else:
                return 'declining'
        else:
            # For pH and chlorine, need to check if moving toward optimal range
            if abs(slope) < 0.001:
                return 'stable'
            return 'variable'

    def _check_compliance(self, parameter: str, value: float) -> Dict[str, Any]:
        """Check if current value meets standards"""
        if parameter not in self.standards:
            return {'status': 'unknown', 'standard': None}

        standard = self.standards[parameter]

        # Check against max
        if 'max' in standard:
            if value <= standard['max']:
                return {'status': 'compliant', 'standard': standard['max'], 'type': 'max'}
            elif 'acceptable' in standard and value <= standard['acceptable']:
                return {'status': 'acceptable', 'standard': standard['acceptable'], 'type': 'max'}
            else:
                return {'status': 'non_compliant', 'standard': standard['max'], 'type': 'max'}

        # Check against min
        if 'min' in standard:
            if value >= standard['min']:
                return {'status': 'compliant', 'standard': standard['min'], 'type': 'min'}
            else:
                return {'status': 'non_compliant', 'standard': standard['min'], 'type': 'min'}

        return {'status': 'unknown', 'standard': None}

    def _calculate_overall_trend(self, parameter_trends: Dict) -> str:
        """Calculate overall site trend from individual parameters"""
        if not parameter_trends:
            return 'unknown'

        trend_scores = []
        for param, trend_data in parameter_trends.items():
            if trend_data['trend'] == 'improving':
                trend_scores.append(1)
            elif trend_data['trend'] == 'declining':
                trend_scores.append(-1)
            else:
                trend_scores.append(0)

        avg_score = np.mean(trend_scores)

        if avg_score > 0.3:
            return 'improving'
        elif avg_score < -0.3:
            return 'declining'
        else:
            return 'stable'

    def _detect_change_points(self, time_series_data: Dict) -> List[Dict]:
        """Detect significant change points in water quality"""
        change_points = []

        for param, data in time_series_data.items():
            values = data['values']
            dates = data['dates']

            if len(values) < 10:  # Need sufficient data
                continue

            # Calculate moving average
            window = min(5, len(values) // 3)
            if window < 2:
                continue

            # Simple moving average
            moving_avg = np.convolve(values, np.ones(window)/window, mode='valid')

            # Pad to match length
            padding = len(values) - len(moving_avg)
            moving_avg = np.concatenate([np.full(padding, np.nan), moving_avg])

            # Find points where change exceeds threshold
            threshold = np.std(values) * 1.5

            for i in range(window, len(values) - 1):
                if not np.isnan(moving_avg[i]) and abs(values[i] - moving_avg[i]) > threshold:
                    change_points.append({
                        'parameter': param,
                        'date': dates[i].isoformat() if hasattr(dates[i], 'isoformat') else str(dates[i]),
                        'value': float(values[i]),
                        'expected': float(moving_avg[i]),
                        'deviation': float(values[i] - moving_avg[i])
                    })

        return change_points[:10]  # Return top 10 most significant

    def _calculate_warning_score(self, parameter_trends: Dict) -> float:
        """
        Calculate early warning score (0-100)
        Higher score = greater concern
        """
        score = 0.0
        weights = {
            'total_coliform_mpn': 20,
            'turbidity_ntu': 12,
            'free_chlorine_mg_l': 10,
            'ammonia_mg_l': 10,
            'iron_mg_l': 8,
            'ph_value': 8,
            'tds_ppm': 8,
            'chloride_mg_l': 6,
            'conductivity_us_cm': 5,
            'temperature_celsius': 5
        }

        for param, trend_data in parameter_trends.items():
            weight = weights.get(param, 5)

            # Add score based on compliance
            if trend_data['compliance']['status'] == 'non_compliant':
                score += weight * 0.5

            # Add score based on trend
            if trend_data['trend'] == 'declining':
                score += weight * 0.3

            # Add score for high variability
            if trend_data['data_points'] > 5:
                cv = trend_data['std_dev'] / trend_data['mean_value'] if trend_data['mean_value'] > 0 else 0
                if cv > 0.5:  # High coefficient of variation
                    score += weight * 0.2

        return min(100.0, score)

    def _get_warning_level(self, score: float) -> str:
        """Convert warning score to level"""
        if score >= 70:
            return 'critical'
        elif score >= 50:
            return 'high'
        elif score >= 30:
            return 'medium'
        else:
            return 'low'

    def _generate_recommendations(self, parameter_trends: Dict, warning_score: float) -> List[str]:
        """Generate actionable recommendations based on trends"""
        recommendations = []

        # Check for declining trends
        declining_params = [
            p for p, data in parameter_trends.items()
            if data['trend'] == 'declining'
        ]

        if declining_params:
            readable_params = [p.replace('_', ' ').replace(' ntu', '').replace(' ppm', '').replace(' mg l', '')
                            for p in declining_params]
            recommendations.append(
                f"Water quality declining for: {', '.join(readable_params)}. "
                "Recommend immediate investigation and corrective action."
            )

        # Check for non-compliance
        non_compliant = [
            p for p, data in parameter_trends.items()
            if data['compliance']['status'] == 'non_compliant'
        ]

        if non_compliant:
            readable_params = [p.replace('_', ' ').replace(' ntu', '').replace(' ppm', '').replace(' mg l', '')
                            for p in non_compliant]
            recommendations.append(
                f"Parameters exceeding standards: {', '.join(readable_params)}. "
                "Immediate treatment intervention required."
            )

        # Check for bacteria
        if 'total_coliform_mpn' in parameter_trends:
            if parameter_trends['total_coliform_mpn']['current_value'] > 0:
                recommendations.append(
                    "Coliform bacteria detected. Implement disinfection protocol immediately."
                )

        # Check chlorine levels
        if 'free_chlorine_mg_l' in parameter_trends:
            chlorine = parameter_trends['free_chlorine_mg_l']['current_value']
            if chlorine < 0.2:
                recommendations.append(
                    "Free chlorine below minimum (0.2 mg/L). Increase chlorination."
                )

        # Overall warning
        if warning_score >= 70:
            recommendations.append(
                "CRITICAL: Multiple parameters show concerning trends. "
                "Immediate comprehensive water quality assessment required."
            )
        elif warning_score >= 50:
            recommendations.append(
                "WARNING: Water quality trends require attention. "
                "Schedule intervention within 2 weeks."
            )

        if not recommendations:
            recommendations.append(
                "Water quality trends are stable. Continue routine monitoring."
            )

        return recommendations

    def get_parameter_forecast(self, site_id: int, parameter: str, days_ahead: int = 90) -> Optional[Dict]:
        """
        Simple forecast for a parameter using linear extrapolation
        """
        # Get historical data (last 6 months)
        cutoff_date = datetime.now() - timedelta(days=180)
        samples = WaterSample.query.filter(
            WaterSample.site_id == site_id,
            WaterSample.collection_date >= cutoff_date
        ).order_by(WaterSample.collection_date).all()

        time_series_data = self._build_time_series(samples)

        if parameter not in time_series_data:
            return None

        data = time_series_data[parameter]
        values = data['values']
        timestamps = np.array(data['timestamps'])

        if len(values) < 5:
            return None

        # Fit linear model
        try:
            coefficients = np.polyfit(timestamps, values, 1)
            slope = coefficients[0]
            intercept = coefficients[1]

            # Calculate R-squared
            predicted = np.polyval(coefficients, timestamps)
            ss_res = np.sum((values - predicted) ** 2)
            ss_tot = np.sum((values - np.mean(values)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        except Exception:
            return None

        # Generate forecast
        last_timestamp = timestamps[-1]
        future_timestamps = [
            last_timestamp + (i * 86400) for i in range(1, days_ahead + 1)
        ]
        forecast_values = [slope * t + intercept for t in future_timestamps]

        # Calculate confidence intervals (simple approach)
        residuals = values - (slope * np.array(timestamps) + intercept)
        std_residual = np.std(residuals)

        return {
            'parameter': parameter,
            'forecast_days': days_ahead,
            'forecast_dates': [
                datetime.fromtimestamp(t).strftime('%Y-%m-%d')
                for t in future_timestamps
            ],
            'forecast_values': [round(v, 3) for v in forecast_values],
            'confidence_interval': float(round(2 * std_residual, 3)),  # ~95% CI
            'model_r_squared': float(round(r_squared, 4)),
            'trend_direction': 'increasing' if slope > 0 else 'decreasing'
        }
