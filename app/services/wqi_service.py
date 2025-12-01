"""
Water Quality Index (WQI) Service
Implements penalty-based WQI calculation algorithm
Based on POC implementation in ronald_results/ALL_MODELS/realtime_wqi_algorithm_poc/
"""
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class WQIService:
    """
    Water Quality Index Calculator

    Calculates WQI score (0-100) using penalty-based aggregation:
    WQI = 100 - Σ P_i(param_i)

    where P_i are penalty functions for each water quality parameter.
    """

    # Compliance thresholds
    EXCELLENT_THRESHOLD = 90.0
    COMPLIANT_THRESHOLD = 70.0
    WARNING_THRESHOLD = 50.0

    # Maximum penalties for each parameter
    MAX_PENALTIES = {
        'ph': 20.0,
        'tds': 30.0,
        'turbidity': 20.0,
        'chlorine': 15.0,
        'temperature': 10.0,
        'coliform': 25.0
    }

    @staticmethod
    def calculate_ph_penalty(ph_value: Optional[float]) -> float:
        """
        Calculate pH penalty (max 20 points)

        Optimal range: 6.5 - 8.5
        Formula (Equation 25):
        - if pH < 6.5: penalty = min(20, 10 × (6.5 - pH))
        - if pH > 8.5: penalty = min(20, 10 × (pH - 8.5))
        - else: penalty = 0

        Args:
            ph_value: pH measurement (typically 0-14)

        Returns:
            Penalty score (0-20)
        """
        if ph_value is None:
            return 0.0

        if ph_value < 6.5:
            penalty = 10.0 * (6.5 - ph_value)
        elif ph_value > 8.5:
            penalty = 10.0 * (ph_value - 8.5)
        else:
            penalty = 0.0

        return min(penalty, WQIService.MAX_PENALTIES['ph'])

    @staticmethod
    def calculate_tds_penalty(tds_ppm: Optional[float]) -> float:
        """
        Calculate TDS (Total Dissolved Solids) penalty (max 30 points)

        Formula (Equation 26):
        - if TDS ≤ 500: penalty = 0
        - if 500 < TDS ≤ 1000: penalty = (TDS - 500) / 20
        - if TDS > 1000: penalty = 25 + min(5, (TDS - 1000) / 200)

        Args:
            tds_ppm: TDS in parts per million (ppm)

        Returns:
            Penalty score (0-30)
        """
        if tds_ppm is None:
            return 0.0

        if tds_ppm <= 500:
            penalty = 0.0
        elif tds_ppm <= 1000:
            penalty = (tds_ppm - 500) / 20.0
        else:
            penalty = 25.0 + min(5.0, (tds_ppm - 1000) / 200.0)

        return min(penalty, WQIService.MAX_PENALTIES['tds'])

    @staticmethod
    def calculate_turbidity_penalty(turbidity_ntu: Optional[float]) -> float:
        """
        Calculate turbidity penalty (max 20 points)

        Formula:
        - if turbidity ≤ 5 NTU: penalty = 0
        - if turbidity > 5 NTU: penalty = min(20, (turbidity - 5) × 4)

        Args:
            turbidity_ntu: Turbidity in Nephelometric Turbidity Units (NTU)

        Returns:
            Penalty score (0-20)
        """
        if turbidity_ntu is None:
            return 0.0

        if turbidity_ntu <= 5.0:
            penalty = 0.0
        else:
            penalty = (turbidity_ntu - 5.0) * 4.0

        return min(penalty, WQIService.MAX_PENALTIES['turbidity'])

    @staticmethod
    def calculate_chlorine_penalty(free_chlorine: Optional[float]) -> float:
        """
        Calculate free chlorine penalty (max 15 points)

        Optimal range: 0.2 - 4.0 mg/L
        Formula:
        - if chlorine < 0.2: penalty = min(15, (0.2 - chlorine) × 30)
        - if chlorine > 4.0: penalty = min(15, (chlorine - 4.0) × 5)
        - else: penalty = 0

        Args:
            free_chlorine: Free chlorine in mg/L

        Returns:
            Penalty score (0-15)
        """
        if free_chlorine is None:
            return 0.0

        if free_chlorine < 0.2:
            penalty = (0.2 - free_chlorine) * 30.0
        elif free_chlorine > 4.0:
            penalty = (free_chlorine - 4.0) * 5.0
        else:
            penalty = 0.0

        return min(penalty, WQIService.MAX_PENALTIES['chlorine'])

    @staticmethod
    def calculate_temperature_penalty(temperature_c: Optional[float]) -> float:
        """
        Calculate temperature penalty (max 10 points)

        Optimal range: 10 - 25°C
        Formula:
        - if temp < 10 or temp > 25: penalty = min(10, |temp - optimal| × 2)
        - else: penalty = 0

        Args:
            temperature_c: Temperature in Celsius

        Returns:
            Penalty score (0-10)
        """
        if temperature_c is None:
            return 0.0

        if temperature_c < 10.0:
            penalty = (10.0 - temperature_c) * 2.0
        elif temperature_c > 25.0:
            penalty = (temperature_c - 25.0) * 2.0
        else:
            penalty = 0.0

        return min(penalty, WQIService.MAX_PENALTIES['temperature'])

    @staticmethod
    def calculate_coliform_penalty(total_coliform: Optional[float]) -> float:
        """
        Calculate total coliform penalty (max 25 points)

        Formula:
        - if coliform ≤ 10 CFU/100mL: penalty = coliform × 0.1
        - if coliform > 10: penalty = min(25, 1.0 + (coliform - 10) × 0.2)

        Args:
            total_coliform: Total coliform count in CFU/100mL

        Returns:
            Penalty score (0-25)
        """
        if total_coliform is None:
            return 0.0

        if total_coliform <= 10.0:
            penalty = total_coliform * 0.1
        else:
            penalty = 1.0 + (total_coliform - 10.0) * 0.2

        return min(penalty, WQIService.MAX_PENALTIES['coliform'])

    @staticmethod
    def classify_compliance(wqi_score: float) -> str:
        """
        Classify WQI score into compliance categories

        Categories:
        - Excellent: WQI ≥ 90
        - Compliant: 70 ≤ WQI < 90 (Safe to drink)
        - Warning: 50 ≤ WQI < 70 (Treatment recommended)
        - Unsafe: WQI < 50 (Not safe to drink)

        Args:
            wqi_score: WQI score (0-100)

        Returns:
            Compliance class string
        """
        if wqi_score >= WQIService.EXCELLENT_THRESHOLD:
            return 'excellent'
        elif wqi_score >= WQIService.COMPLIANT_THRESHOLD:
            return 'compliant'
        elif wqi_score >= WQIService.WARNING_THRESHOLD:
            return 'warning'
        else:
            return 'unsafe'

    @staticmethod
    def is_safe_to_drink(wqi_score: float) -> bool:
        """
        Determine if water is safe to drink

        Safe threshold: WQI ≥ 70

        Args:
            wqi_score: WQI score (0-100)

        Returns:
            True if safe to drink, False otherwise
        """
        return wqi_score >= WQIService.COMPLIANT_THRESHOLD

    @classmethod
    def calculate_wqi(cls,
                      ph_value: Optional[float] = None,
                      tds_ppm: Optional[float] = None,
                      turbidity_ntu: Optional[float] = None,
                      free_chlorine: Optional[float] = None,
                      temperature_c: Optional[float] = None,
                      total_coliform: Optional[float] = None) -> Dict:
        """
        Calculate Water Quality Index (WQI) from water quality parameters

        Core Formula (Equation 24):
        WQI = 100 - Σ P_i(param_i)

        Args:
            ph_value: pH (6.5-8.5 optimal)
            tds_ppm: Total Dissolved Solids in ppm (≤500 excellent, ≤1000 acceptable)
            turbidity_ntu: Turbidity in NTU (≤5 acceptable)
            free_chlorine: Free chlorine in mg/L (0.2-4.0 optimal)
            temperature_c: Temperature in °C (10-25 optimal)
            total_coliform: Total coliform in CFU/100mL (≤10 acceptable)

        Returns:
            Dictionary with:
                - wqi_score: Overall WQI score (0-100)
                - compliance_class: Classification (excellent/compliant/warning/unsafe)
                - is_safe: Boolean indicating if safe to drink
                - penalties: Breakdown of individual penalties
                - total_penalty: Sum of all penalties
        """
        # Calculate individual penalties
        ph_penalty = cls.calculate_ph_penalty(ph_value)
        tds_penalty = cls.calculate_tds_penalty(tds_ppm)
        turbidity_penalty = cls.calculate_turbidity_penalty(turbidity_ntu)
        chlorine_penalty = cls.calculate_chlorine_penalty(free_chlorine)
        temperature_penalty = cls.calculate_temperature_penalty(temperature_c)
        coliform_penalty = cls.calculate_coliform_penalty(total_coliform)

        # Sum all penalties
        total_penalty = (
            ph_penalty +
            tds_penalty +
            turbidity_penalty +
            chlorine_penalty +
            temperature_penalty +
            coliform_penalty
        )

        # Calculate WQI score
        wqi_score = max(0.0, 100.0 - total_penalty)

        # Classify compliance
        compliance_class = cls.classify_compliance(wqi_score)
        is_safe = cls.is_safe_to_drink(wqi_score)

        logger.info(f"WQI calculation: score={wqi_score:.2f}, class={compliance_class}, safe={is_safe}")

        return {
            'wqi_score': round(wqi_score, 2),
            'compliance_class': compliance_class,
            'is_safe': is_safe,
            'penalties': {
                'ph': round(ph_penalty, 2),
                'tds': round(tds_penalty, 2),
                'turbidity': round(turbidity_penalty, 2),
                'chlorine': round(chlorine_penalty, 2),
                'temperature': round(temperature_penalty, 2),
                'coliform': round(coliform_penalty, 2)
            },
            'total_penalty': round(total_penalty, 2),
            'input_parameters': {
                'ph_value': ph_value,
                'tds_ppm': tds_ppm,
                'turbidity_ntu': turbidity_ntu,
                'free_chlorine': free_chlorine,
                'temperature_c': temperature_c,
                'total_coliform': total_coliform
            }
        }

    @classmethod
    def get_compliance_info(cls, compliance_class: str) -> Dict:
        """
        Get detailed information about a compliance class

        Args:
            compliance_class: Compliance classification

        Returns:
            Dictionary with description, color, and recommendations
        """
        compliance_info = {
            'excellent': {
                'description': 'Water quality exceeds safety standards',
                'color': '#28a745',  # Green
                'badge_class': 'success',
                'icon': 'bi-check-circle-fill',
                'recommendation': 'Safe to drink. Excellent water quality.',
                'action': None
            },
            'compliant': {
                'description': 'Water quality meets safety standards',
                'color': '#17a2b8',  # Blue
                'badge_class': 'info',
                'icon': 'bi-check-circle',
                'recommendation': 'Safe to drink. Water quality is acceptable.',
                'action': 'Continue regular monitoring.'
            },
            'warning': {
                'description': 'Water quality needs attention',
                'color': '#ffc107',  # Yellow
                'badge_class': 'warning',
                'icon': 'bi-exclamation-triangle',
                'recommendation': 'Treatment recommended before consumption.',
                'action': 'Boil water for 15 minutes or use water purifier.'
            },
            'unsafe': {
                'description': 'Water quality is unsafe',
                'color': '#dc3545',  # Red
                'badge_class': 'danger',
                'icon': 'bi-x-circle-fill',
                'recommendation': 'Not safe to drink. Do not consume.',
                'action': 'Use alternative water source immediately. Report to authorities.'
            }
        }

        return compliance_info.get(compliance_class, compliance_info['unsafe'])
