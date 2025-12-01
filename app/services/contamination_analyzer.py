"""
Contamination Analyzer - Rule-based water quality analysis
Implements the contamination classification logic based on test parameters
"""
from app.models.analysis import Analysis
import json


class ContaminationAnalyzer:
    """Analyzes water samples using rule-based classification"""

    # WHO and BIS Standards (simplified - should be comprehensive in production)
    STANDARDS = {
        'WHO': {
            'turbidity_ntu': 5.0,
            'ph_min': 6.5,
            'ph_max': 8.5,
            'tds_ppm': 1000.0,
            'free_chlorine_mg_l': 0.2,
            'iron_mg_l': 0.3,
            'nitrate_mg_l': 50.0,
            'fluoride_mg_l': 1.5
        },
        'BIS': {
            'turbidity_ntu': 5.0,
            'ph_min': 6.5,
            'ph_max': 8.5,
            'tds_ppm': 500.0,  # More stringent
            'free_chlorine_mg_l': 0.2,
            'iron_mg_l': 0.3,
            'nitrate_mg_l': 45.0,
            'fluoride_mg_l': 1.0
        }
    }

    def analyze_sample(self, sample, test_result):
        """
        Perform comprehensive analysis on a water sample
        Returns Analysis object (not yet committed to database)
        """
        analysis = Analysis(
            sample_id=sample.id,
            test_result_id=test_result.id
        )

        # Run all classification rules
        self._analyze_runoff_sediment(sample, test_result, analysis)
        self._analyze_sewage_ingress(sample, test_result, analysis)
        self._analyze_salt_intrusion(sample, test_result, analysis)
        self._analyze_pipe_corrosion(sample, test_result, analysis)
        self._analyze_disinfectant_decay(sample, test_result, analysis)

        # Determine primary cause and severity
        self._determine_primary_cause(analysis)
        self._check_compliance(test_result, analysis)
        self._generate_recommendations(sample, test_result, analysis)

        return analysis

    def _analyze_runoff_sediment(self, sample, test_result, analysis):
        """Rule: Turbidity > 5 NTU AND Rained Recently = Yes"""
        score = 0.0
        indicators = []

        if test_result.turbidity_ntu and test_result.turbidity_ntu > 5.0:
            score += 0.5
            indicators.append(f"High turbidity: {test_result.turbidity_ntu} NTU (threshold: 5.0)")

        if sample.rained_recently:
            score += 0.5
            indicators.append(f"Recent rainfall (days since rain: {sample.days_since_rain or 0})")

        # Additional indicators
        if hasattr(sample, 'environment_type') and sample.environment_type in ['rural', 'marshland']:
            score += 0.2
            indicators.append(f"Environment type: {sample.environment_type}")

        if hasattr(sample, 'visible_particles') and sample.visible_particles:
            score += 0.15
            indicators.append("Visible particles observed")

        analysis.runoff_sediment_score = min(score, 1.0)
        analysis.set_indicators('runoff_sediment', indicators)

    def _analyze_sewage_ingress(self, sample, test_result, analysis):
        """Rule: Coliform Positive OR (Free Chlorine < 0.2 AND Odor Present)"""
        score = 0.0
        indicators = []

        if test_result.coliform_status == 'positive':
            score += 0.7
            indicators.append(f"Coliform positive")
            if test_result.coliform_count_cfu_100ml:
                indicators.append(f"Coliform count: {test_result.coliform_count_cfu_100ml} CFU/100ml")

        if test_result.e_coli_status == 'positive':
            score += 0.8
            indicators.append("E. coli positive")

        if test_result.free_chlorine_mg_l is not None and test_result.free_chlorine_mg_l < 0.2:
            score += 0.3
            indicators.append(f"Low free chlorine: {test_result.free_chlorine_mg_l} mg/L (threshold: 0.2)")

            if sample.odor_present:
                score += 0.4
                indicators.append(f"Odor present: {sample.odor_description or 'unspecified'}")

        # Additional indicators
        if test_result.ammonia_mg_l and test_result.ammonia_mg_l > 0.5:
            score += 0.3
            indicators.append(f"Elevated ammonia: {test_result.ammonia_mg_l} mg/L")

        if test_result.nitrite_mg_l and test_result.nitrite_mg_l > 3.0:
            score += 0.2
            indicators.append(f"Elevated nitrite: {test_result.nitrite_mg_l} mg/L")

        analysis.sewage_ingress_score = min(score, 1.0)
        analysis.set_indicators('sewage_ingress', indicators)

    def _analyze_salt_intrusion(self, sample, test_result, analysis):
        """Rule: TDS > 1000 ppm AND Coastal Area AND Pipe != GI"""
        score = 0.0
        indicators = []

        if test_result.tds_ppm and test_result.tds_ppm > 1000.0:
            score += 0.5
            indicators.append(f"High TDS: {test_result.tds_ppm} ppm (threshold: 1000)")

        if sample.site and sample.site.is_coastal:
            score += 0.4
            indicators.append("Coastal location")

        if sample.pipe_material and sample.pipe_material.upper() not in ['GI', 'IRON']:
            score += 0.2
            indicators.append(f"Non-GI pipe: {sample.pipe_material}")

        # Additional indicators
        if test_result.salinity_ppm and test_result.salinity_ppm > 500:
            score += 0.3
            indicators.append(f"High salinity: {test_result.salinity_ppm} ppm")

        if test_result.chloride_mg_l and test_result.chloride_mg_l > 250:
            score += 0.2
            indicators.append(f"High chloride: {test_result.chloride_mg_l} mg/L")

        if test_result.conductivity_us_cm and test_result.conductivity_us_cm > 2000:
            score += 0.2
            indicators.append(f"High conductivity: {test_result.conductivity_us_cm} µS/cm")

        analysis.salt_intrusion_score = min(score, 1.0)
        analysis.set_indicators('salt_intrusion', indicators)

    def _analyze_pipe_corrosion(self, sample, test_result, analysis):
        """Rule: Iron > 0.3 mg/L AND Pipe = GI/Iron AND Age >= 5 years"""
        score = 0.0
        indicators = []

        if test_result.iron_mg_l and test_result.iron_mg_l > 0.3:
            score += 0.5
            indicators.append(f"High iron: {test_result.iron_mg_l} mg/L (threshold: 0.3)")

        if sample.pipe_material and sample.pipe_material.upper() in ['GI', 'IRON']:
            score += 0.3
            indicators.append(f"GI/Iron pipe: {sample.pipe_material}")

            if sample.pipe_age_years and sample.pipe_age_years >= 5:
                score += 0.3
                indicators.append(f"Pipe age: {sample.pipe_age_years} years (threshold: 5)")

        # Additional indicators
        if test_result.manganese_mg_l and test_result.manganese_mg_l > 0.1:
            score += 0.2
            indicators.append(f"Elevated manganese: {test_result.manganese_mg_l} mg/L")

        if test_result.ph_value and test_result.ph_value < 6.5:
            score += 0.2
            indicators.append(f"Low pH (corrosive): {test_result.ph_value}")

        if test_result.lead_mg_l and test_result.lead_mg_l > 0.01:
            score += 0.3
            indicators.append(f"Elevated lead: {test_result.lead_mg_l} mg/L")

        analysis.pipe_corrosion_score = min(score, 1.0)
        analysis.set_indicators('pipe_corrosion', indicators)

    def _analyze_disinfectant_decay(self, sample, test_result, analysis):
        """Rule: Free Chlorine < 0.2 AND Distance from Source = Far"""
        score = 0.0
        indicators = []

        if test_result.free_chlorine_mg_l is not None and test_result.free_chlorine_mg_l < 0.2:
            score += 0.5
            indicators.append(f"Low free chlorine: {test_result.free_chlorine_mg_l} mg/L (threshold: 0.2)")

        if sample.distance_from_source_meters:
            if sample.distance_from_source_meters > 1000:  # > 1 km considered far
                score += 0.4
                indicators.append(f"Distance from source: {sample.distance_from_source_meters}m (far)")
            elif sample.distance_from_source_meters > 500:
                score += 0.2
                indicators.append(f"Distance from source: {sample.distance_from_source_meters}m (moderate)")

        # Additional indicators
        if sample.storage_type and sample.storage_type != 'direct_source':
            score += 0.2
            indicators.append(f"Storage present: {sample.storage_type}")

        if sample.source_age_years and sample.source_age_years > 10:
            score += 0.15
            indicators.append(f"Old water source: {sample.source_age_years} years")

        analysis.disinfectant_decay_score = min(score, 1.0)
        analysis.set_indicators('disinfectant_decay', indicators)

    def _determine_primary_cause(self, analysis):
        """Determine primary contamination cause from scores"""
        scores = {
            'runoff_sediment': analysis.runoff_sediment_score or 0,
            'sewage_ingress': analysis.sewage_ingress_score or 0,
            'salt_intrusion': analysis.salt_intrusion_score or 0,
            'pipe_corrosion': analysis.pipe_corrosion_score or 0,
            'disinfectant_decay': analysis.disinfectant_decay_score or 0
        }

        max_score = max(scores.values())

        if max_score >= 0.4:  # Threshold for contamination detection
            analysis.contamination_detected = True
            analysis.primary_cause = max(scores.items(), key=lambda x: x[1])[0]
            analysis.confidence_level = max_score

            # Determine severity based on score
            if max_score >= 0.8:
                analysis.severity = 'critical'
            elif max_score >= 0.6:
                analysis.severity = 'high'
            elif max_score >= 0.4:
                analysis.severity = 'medium'
            else:
                analysis.severity = 'low'
        else:
            analysis.contamination_detected = False
            analysis.primary_cause = None
            analysis.severity = 'low'
            analysis.confidence_level = 0.0

    def _check_compliance(self, test_result, analysis):
        """Check WHO and BIS compliance"""
        who_compliant = True
        bis_compliant = True
        non_compliant_params = []

        # Check each parameter against standards
        if test_result.turbidity_ntu and test_result.turbidity_ntu > self.STANDARDS['WHO']['turbidity_ntu']:
            who_compliant = False
            non_compliant_params.append('turbidity')
            if test_result.turbidity_ntu > self.STANDARDS['BIS']['turbidity_ntu']:
                bis_compliant = False

        if test_result.ph_value:
            if test_result.ph_value < self.STANDARDS['WHO']['ph_min'] or \
               test_result.ph_value > self.STANDARDS['WHO']['ph_max']:
                who_compliant = False
                bis_compliant = False
                non_compliant_params.append('ph')

        if test_result.tds_ppm:
            if test_result.tds_ppm > self.STANDARDS['WHO']['tds_ppm']:
                who_compliant = False
                non_compliant_params.append('tds')
            if test_result.tds_ppm > self.STANDARDS['BIS']['tds_ppm']:
                bis_compliant = False

        if test_result.free_chlorine_mg_l is not None and \
           test_result.free_chlorine_mg_l < self.STANDARDS['WHO']['free_chlorine_mg_l']:
            who_compliant = False
            bis_compliant = False
            non_compliant_params.append('free_chlorine')

        if test_result.iron_mg_l and test_result.iron_mg_l > self.STANDARDS['WHO']['iron_mg_l']:
            who_compliant = False
            bis_compliant = False
            non_compliant_params.append('iron')

        analysis.who_compliant = who_compliant
        analysis.bis_compliant = bis_compliant
        analysis.non_compliant_parameters = json.dumps(non_compliant_params)

    def _generate_recommendations(self, sample, test_result, analysis):
        """Generate remediation recommendations based on analysis"""
        immediate = []
        short_term = []
        long_term = []
        priority = 'normal'

        if analysis.contamination_detected:
            cause = analysis.primary_cause

            if cause == 'runoff_sediment':
                immediate.append("Install sediment filter at point of use")
                immediate.append("Boil water before consumption")
                short_term.append("Implement proper drainage around water source")
                short_term.append("Install settling tank")
                long_term.append("Relocate intake point away from runoff areas")
                long_term.append("Implement watershed protection measures")
                priority = 'high' if analysis.severity in ['high', 'critical'] else 'urgent'

            elif cause == 'sewage_ingress':
                immediate.append("DO NOT CONSUME - Potential sewage contamination")
                immediate.append("Chlorinate water source immediately")
                short_term.append("Inspect and repair sewage lines near water source")
                short_term.append("Implement proper septic system maintenance")
                long_term.append("Upgrade sewage infrastructure")
                long_term.append("Relocate water source if septic contamination persists")
                priority = 'immediate'

            elif cause == 'salt_intrusion':
                immediate.append("Use reverse osmosis filter")
                short_term.append("Test alternative water sources")
                short_term.append("Reduce groundwater extraction rate")
                long_term.append("Implement coastal aquifer management")
                long_term.append("Consider alternative water source (rainwater harvesting)")
                priority = 'urgent'

            elif cause == 'pipe_corrosion':
                immediate.append("Flush pipes regularly until replacement")
                immediate.append("Install corrosion-resistant point-of-use filter")
                short_term.append("Replace corroded pipe sections with PVC/HDPE")
                short_term.append("Install water treatment to adjust pH")
                long_term.append("Complete replacement of GI pipes with PVC/HDPE")
                priority = 'high'

            elif cause == 'disinfectant_decay':
                immediate.append("Install point-of-use chlorination")
                short_term.append("Increase chlorine dosage at source")
                short_term.append("Reduce storage time")
                short_term.append("Clean storage tanks")
                long_term.append("Install booster chlorination stations")
                long_term.append("Upgrade distribution system to reduce residence time")
                priority = 'normal'

        analysis.set_recommendations(immediate, short_term, long_term)
        analysis.implementation_priority = priority

        # Set follow-up requirements
        if analysis.severity in ['high', 'critical']:
            analysis.follow_up_required = True
