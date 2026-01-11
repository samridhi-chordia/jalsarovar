"""
Contamination Analyzer Service
Rule-based contamination detection with 5 contamination types
"""
import json
from datetime import datetime
from typing import Dict, Tuple, List, Optional


class ContaminationAnalyzer:
    """
    Rule-based contamination detection service
    Detects 5 types: Runoff/Sediment, Sewage, Salt Intrusion, Pipe Corrosion, Disinfectant Decay
    """

    # Contamination type labels
    CONTAMINATION_TYPES = {
        'runoff_sediment': 'Runoff/Sediment',
        'sewage_ingress': 'Sewage Ingress',
        'salt_intrusion': 'Salt Intrusion',
        'pipe_corrosion': 'Pipe Corrosion',
        'disinfectant_decay': 'Disinfectant Decay'
    }

    # Treatment recommendations by contamination type
    TREATMENT_RECOMMENDATIONS = {
        'runoff_sediment': {
            'primary': 'Install sediment filters and settling tanks',
            'secondary': [
                'Construct bunds around water body',
                'Plant vegetation buffers',
                'Schedule post-monsoon cleaning'
            ],
            'cost_range': (50000, 200000)
        },
        'sewage_ingress': {
            'primary': 'Repair sewage infrastructure and install chlorination',
            'secondary': [
                'Conduct pipe integrity survey',
                'Install UV treatment system',
                'Establish regular chlorine dosing'
            ],
            'cost_range': (100000, 500000)
        },
        'salt_intrusion': {
            'primary': 'Install freshwater injection wells and barriers',
            'secondary': [
                'Reduce groundwater extraction',
                'Install reverse osmosis system',
                'Monitor salinity trends'
            ],
            'cost_range': (200000, 1000000)
        },
        'pipe_corrosion': {
            'primary': 'Replace corroded GI pipes with HDPE/PVC',
            'secondary': [
                'Add corrosion inhibitors',
                'Install iron removal filters',
                'Conduct pipe condition assessment'
            ],
            'cost_range': (75000, 300000)
        },
        'disinfectant_decay': {
            'primary': 'Install booster chlorination stations',
            'secondary': [
                'Reduce water age in distribution',
                'Clean and flush pipelines',
                'Add chlorine reservoirs at key points'
            ],
            'cost_range': (30000, 150000)
        }
    }

    def analyze(self, test_result, sample, site) -> Dict:
        """
        Perform comprehensive contamination analysis

        Args:
            test_result: TestResult model instance
            sample: WaterSample model instance
            site: Site model instance

        Returns:
            Dictionary with analysis results
        """
        # Calculate individual contamination scores
        scores = {
            'runoff_sediment': self._score_runoff_sediment(test_result, sample, site),
            'sewage_ingress': self._score_sewage_ingress(test_result, sample, site),
            'salt_intrusion': self._score_salt_intrusion(test_result, sample, site),
            'pipe_corrosion': self._score_pipe_corrosion(test_result, sample, site),
            'disinfectant_decay': self._score_disinfectant_decay(test_result, sample, site)
        }

        # Determine primary contamination
        max_score = max(scores.values())
        is_contaminated = max_score >= 0.3  # 30% threshold

        if is_contaminated:
            primary_type = max(scores, key=scores.get)
            confidence = min(100, max_score * 100)
        else:
            primary_type = None
            confidence = 100 - (max_score * 100)  # Confidence in being clean

        # Determine severity
        severity = self._determine_severity(max_score)

        # Calculate WQI with data quality assessment
        wqi_result = test_result.calculate_wqi()
        wqi_class, wqi_status = test_result.get_wqi_class()

        # Check compliance
        who_compliant, who_violations = test_result.check_who_compliance()
        bis_compliant, bis_violations = test_result.check_bis_compliance()

        # Get recommendations
        recommendations = self._get_recommendations(primary_type, severity)

        # Build result
        result = {
            'is_contaminated': is_contaminated,
            'contamination_type': self.CONTAMINATION_TYPES.get(primary_type) if primary_type else 'None Detected',
            'contamination_type_key': primary_type,
            'severity_level': severity,
            'confidence_score': round(confidence, 1),

            # Individual scores
            'runoff_sediment_score': round(scores['runoff_sediment'], 3),
            'sewage_ingress_score': round(scores['sewage_ingress'], 3),
            'salt_intrusion_score': round(scores['salt_intrusion'], 3),
            'pipe_corrosion_score': round(scores['pipe_corrosion'], 3),
            'disinfectant_decay_score': round(scores['disinfectant_decay'], 3),

            # WQI with data quality metrics
            'wqi_score': round(wqi_result['wqi_score'], 1),
            'wqi_class': wqi_class,
            'wqi_status': wqi_status,
            'data_coverage_pct': wqi_result['data_coverage_pct'],
            'parameters_measured': wqi_result['parameters_measured'],
            'key_parameters_measured': wqi_result['key_parameters_measured'],
            'has_sufficient_data': wqi_result['has_sufficient_data'],
            'data_quality_tier': wqi_result['data_quality_tier'],

            # Compliance
            'is_compliant_who': who_compliant,
            'is_compliant_bis': bis_compliant,
            'who_violations': json.dumps(who_violations),
            'bis_violations': json.dumps(bis_violations),

            # Recommendations
            'primary_recommendation': recommendations['primary'],
            'secondary_recommendations': json.dumps(recommendations['secondary']),
            'estimated_treatment_cost_inr': recommendations['cost_estimate'],
            'treatment_urgency': self._determine_urgency(severity),

            # Metadata
            'analysis_method': 'rule_based',
            'analysis_date': datetime.utcnow()
        }

        return result

    def _score_runoff_sediment(self, test_result, sample, site) -> float:
        """Score for runoff/sediment contamination"""
        score = 0.0

        # High turbidity indicator
        if test_result.turbidity_ntu:
            if test_result.turbidity_ntu > 10:
                score += 0.4
            elif test_result.turbidity_ntu > 5:
                score += 0.2

        # Color indicator
        if test_result.color_hazen:
            if test_result.color_hazen > 25:
                score += 0.2
            elif test_result.color_hazen > 15:
                score += 0.1

        # Recent rainfall
        if sample.rained_recently:
            score += 0.25

        if sample.rainfall_mm_24h and sample.rainfall_mm_24h > 20:
            score += 0.15

        # Agricultural area
        if site.is_agricultural_nearby:
            score += 0.1

        # Seasonal factor (monsoon)
        if sample.weather_condition in ['rainy', 'stormy']:
            score += 0.1

        return min(1.0, score)

    def _score_sewage_ingress(self, test_result, sample, site) -> float:
        """Score for sewage ingress contamination"""
        score = 0.0

        # Coliform presence - strong indicator
        if test_result.total_coliform_mpn and test_result.total_coliform_mpn > 0:
            if test_result.total_coliform_mpn > 100:
                score += 0.5
            elif test_result.total_coliform_mpn > 10:
                score += 0.35
            else:
                score += 0.2

        # E. coli - definitive indicator
        if test_result.e_coli_mpn and test_result.e_coli_mpn > 0:
            score += 0.4

        # Ammonia - sewage marker
        if test_result.ammonia_mg_l:
            if test_result.ammonia_mg_l > 1.5:
                score += 0.2
            elif test_result.ammonia_mg_l > 0.5:
                score += 0.1

        # Low chlorine allows bacterial growth
        if test_result.free_chlorine_mg_l is not None and test_result.free_chlorine_mg_l < 0.2:
            score += 0.15

        # Sewage odor
        if sample.odor and sample.odor.lower() in ['sewage', 'foul', 'septic']:
            score += 0.2

        # Urban area more prone
        if site.is_urban:
            score += 0.05

        return min(1.0, score)

    def _score_salt_intrusion(self, test_result, sample, site) -> float:
        """Score for salt intrusion contamination"""
        score = 0.0

        # High TDS - primary indicator
        if test_result.tds_ppm:
            if test_result.tds_ppm > 2000:
                score += 0.5
            elif test_result.tds_ppm > 1000:
                score += 0.35
            elif test_result.tds_ppm > 500:
                score += 0.15

        # High conductivity
        if test_result.conductivity_us_cm:
            if test_result.conductivity_us_cm > 3000:
                score += 0.25
            elif test_result.conductivity_us_cm > 1500:
                score += 0.15

        # High chloride
        if test_result.chloride_mg_l:
            if test_result.chloride_mg_l > 600:
                score += 0.3
            elif test_result.chloride_mg_l > 250:
                score += 0.15

        # Coastal location - major risk factor
        if site.is_coastal:
            score += 0.25

        # Sodium levels
        if test_result.sodium_mg_l and test_result.sodium_mg_l > 200:
            score += 0.1

        return min(1.0, score)

    def _score_pipe_corrosion(self, test_result, sample, site) -> float:
        """Score for pipe corrosion contamination"""
        score = 0.0

        # Iron levels - primary indicator
        if test_result.iron_mg_l:
            if test_result.iron_mg_l > 1.0:
                score += 0.4
            elif test_result.iron_mg_l > 0.3:
                score += 0.25
            elif test_result.iron_mg_l > 0.1:
                score += 0.1

        # Manganese levels
        if test_result.manganese_mg_l:
            if test_result.manganese_mg_l > 0.4:
                score += 0.25
            elif test_result.manganese_mg_l > 0.1:
                score += 0.1

        # Copper levels (copper pipe corrosion)
        if test_result.copper_mg_l and test_result.copper_mg_l > 1.0:
            score += 0.15

        # Brown/rust color
        if sample.apparent_color and sample.apparent_color.lower() in ['brown', 'rust', 'orange', 'red']:
            score += 0.2

        # Low pH accelerates corrosion
        if test_result.ph and test_result.ph < 6.5:
            score += 0.15

        return min(1.0, score)

    def _score_disinfectant_decay(self, test_result, sample, site) -> float:
        """Score for disinfectant decay contamination"""
        score = 0.0

        # Low chlorine - primary indicator
        if test_result.free_chlorine_mg_l is not None:
            if test_result.free_chlorine_mg_l < 0.1:
                score += 0.4
            elif test_result.free_chlorine_mg_l < 0.2:
                score += 0.25
            elif test_result.free_chlorine_mg_l < 0.5:
                score += 0.1

        # Coliform presence with low chlorine
        if test_result.total_coliform_mpn and test_result.total_coliform_mpn > 0:
            if test_result.free_chlorine_mg_l is not None and test_result.free_chlorine_mg_l < 0.2:
                score += 0.25

        # High water temperature accelerates decay
        if test_result.temperature_celsius and test_result.temperature_celsius > 30:
            score += 0.1

        # High TOC consumes chlorine
        if test_result.toc_mg_l and test_result.toc_mg_l > 4:
            score += 0.1

        # Distant from treatment plant (proxy: rural area, reservoir type)
        if site.site_type in ['tank', 'reservoir'] and not site.is_urban:
            score += 0.1

        return min(1.0, score)

    def _determine_severity(self, max_score: float) -> str:
        """Determine severity level from max contamination score"""
        if max_score >= 0.7:
            return 'critical'
        elif max_score >= 0.5:
            return 'high'
        elif max_score >= 0.3:
            return 'medium'
        else:
            return 'low'

    def _determine_urgency(self, severity: str) -> str:
        """Determine treatment urgency from severity"""
        urgency_map = {
            'critical': 'immediate',
            'high': 'within_week',
            'medium': 'within_month',
            'low': 'routine'
        }
        return urgency_map.get(severity, 'routine')

    def _get_recommendations(self, contamination_type: Optional[str], severity: str) -> Dict:
        """Get treatment recommendations based on contamination type"""
        if not contamination_type or contamination_type not in self.TREATMENT_RECOMMENDATIONS:
            return {
                'primary': 'Continue regular monitoring',
                'secondary': ['Maintain current water quality', 'Schedule routine testing'],
                'cost_estimate': 0
            }

        rec = self.TREATMENT_RECOMMENDATIONS[contamination_type]
        cost_min, cost_max = rec['cost_range']

        # Adjust cost based on severity
        severity_multiplier = {
            'critical': 1.5,
            'high': 1.2,
            'medium': 1.0,
            'low': 0.7
        }
        multiplier = severity_multiplier.get(severity, 1.0)
        cost_estimate = ((cost_min + cost_max) / 2) * multiplier

        return {
            'primary': rec['primary'],
            'secondary': rec['secondary'],
            'cost_estimate': round(cost_estimate, 0)
        }
