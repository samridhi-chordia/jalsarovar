"""Test Result model - Laboratory measurements"""
from datetime import datetime
from app import db


# WQI Data Quality - Key parameters for reliable assessment
KEY_PARAMETERS = ['ph', 'tds_ppm', 'turbidity_ntu', 'free_chlorine_mg_l', 'total_coliform_mpn']
ALL_WQI_PARAMETERS = KEY_PARAMETERS + ['temperature_celsius', 'dissolved_oxygen_mg_l',
                                        'bod_mg_l', 'nitrate_mg_l', 'iron_mg_l']


class TestResult(db.Model):
    """Laboratory test results for water samples - 40+ parameters"""
    __tablename__ = 'test_results'

    id = db.Column(db.Integer, primary_key=True)
    sample_id = db.Column(db.Integer, db.ForeignKey('water_samples.id'), nullable=False, index=True)
    tested_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    tested_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    lab_name = db.Column(db.String(200))
    lab_accreditation = db.Column(db.String(100))

    # Physical Parameters
    ph = db.Column(db.Float)
    temperature_celsius = db.Column(db.Float)
    turbidity_ntu = db.Column(db.Float)
    color_hazen = db.Column(db.Float)
    odor_threshold = db.Column(db.Integer)  # 1-5 scale
    taste_rating = db.Column(db.Integer)  # 1-5 scale
    conductivity_us_cm = db.Column(db.Float)

    # Chemical Parameters - General
    tds_ppm = db.Column(db.Float)  # Total Dissolved Solids
    total_hardness_mg_l = db.Column(db.Float)
    calcium_hardness_mg_l = db.Column(db.Float)
    magnesium_hardness_mg_l = db.Column(db.Float)
    total_alkalinity_mg_l = db.Column(db.Float)

    # Disinfection
    free_chlorine_mg_l = db.Column(db.Float)
    total_chlorine_mg_l = db.Column(db.Float)
    chlorine_residual_mg_l = db.Column(db.Float)

    # Anions
    chloride_mg_l = db.Column(db.Float)
    fluoride_mg_l = db.Column(db.Float)
    sulfate_mg_l = db.Column(db.Float)
    nitrate_mg_l = db.Column(db.Float)
    nitrite_mg_l = db.Column(db.Float)
    phosphate_mg_l = db.Column(db.Float)

    # Cations / Metals
    iron_mg_l = db.Column(db.Float)
    manganese_mg_l = db.Column(db.Float)
    copper_mg_l = db.Column(db.Float)
    zinc_mg_l = db.Column(db.Float)
    lead_mg_l = db.Column(db.Float)
    arsenic_mg_l = db.Column(db.Float)
    chromium_mg_l = db.Column(db.Float)
    cadmium_mg_l = db.Column(db.Float)
    mercury_mg_l = db.Column(db.Float)
    nickel_mg_l = db.Column(db.Float)
    aluminum_mg_l = db.Column(db.Float)
    sodium_mg_l = db.Column(db.Float)
    potassium_mg_l = db.Column(db.Float)

    # Nitrogen compounds
    ammonia_mg_l = db.Column(db.Float)
    total_nitrogen_mg_l = db.Column(db.Float)
    organic_nitrogen_mg_l = db.Column(db.Float)

    # Organic parameters
    dissolved_oxygen_mg_l = db.Column(db.Float)
    bod_mg_l = db.Column(db.Float)  # Biochemical Oxygen Demand
    cod_mg_l = db.Column(db.Float)  # Chemical Oxygen Demand
    toc_mg_l = db.Column(db.Float)  # Total Organic Carbon

    # Microbiological Parameters
    total_coliform_mpn = db.Column(db.Float)  # MPN/100ml
    fecal_coliform_mpn = db.Column(db.Float)
    e_coli_mpn = db.Column(db.Float)
    total_plate_count = db.Column(db.Float)  # CFU/ml

    # Pesticides/Herbicides (if tested)
    pesticides_detected = db.Column(db.Boolean, default=False)
    pesticide_types = db.Column(db.Text)  # JSON list of detected pesticides

    # Metadata
    test_method = db.Column(db.String(100))  # standard method reference
    quality_control_passed = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    analyses = db.relationship('Analysis', backref='test_result', lazy='dynamic')

    def check_who_compliance(self):
        """Check compliance with WHO standards"""
        from flask import current_app
        standards = current_app.config.get('WHO_STANDARDS', {})
        violations = []

        for param, limits in standards.items():
            value = getattr(self, param, None)
            if value is not None:
                if 'min' in limits and value < limits['min']:
                    violations.append((param, value, f"< {limits['min']}"))
                if 'max' in limits and value > limits['max']:
                    violations.append((param, value, f"> {limits['max']}"))

        return len(violations) == 0, violations

    def check_bis_compliance(self):
        """Check compliance with BIS standards"""
        from flask import current_app
        standards = current_app.config.get('BIS_STANDARDS', {})
        violations = []

        for param, limits in standards.items():
            value = getattr(self, param, None)
            if value is not None:
                if 'min' in limits and value < limits['min']:
                    violations.append((param, value, f"< {limits['min']}"))
                if 'max' in limits and value > limits['max']:
                    violations.append((param, value, f"> {limits['max']}"))

        return len(violations) == 0, violations

    def get_parameter_coverage(self):
        """Calculate parameter coverage for data quality assessment"""
        measured_params = []
        key_params_measured = 0

        for param in ALL_WQI_PARAMETERS:
            value = getattr(self, param, None)
            if value is not None:
                measured_params.append(param)
                if param in KEY_PARAMETERS:
                    key_params_measured += 1

        total_coverage = len(measured_params)
        coverage_pct = (total_coverage / len(ALL_WQI_PARAMETERS)) * 100
        has_sufficient = key_params_measured >= 3

        if has_sufficient:
            tier = 'full'
        elif key_params_measured >= 1:
            tier = 'partial'
        else:
            tier = 'insufficient'

        return {
            'parameters_measured': total_coverage,
            'key_parameters_measured': key_params_measured,
            'data_coverage_pct': round(coverage_pct, 1),
            'has_sufficient_data': has_sufficient,
            'data_quality_tier': tier,
            'measured_params': measured_params,
            'missing_key_params': [p for p in KEY_PARAMETERS if getattr(self, p, None) is None]
        }

    def calculate_wqi(self):
        """Calculate Water Quality Index with data quality assessment"""
        # Get coverage info first
        coverage = self.get_parameter_coverage()

        # Calculate base WQI (existing penalty logic unchanged)
        wqi = 100.0

        # pH penalty (optimal: 6.5-8.5)
        if self.ph is not None:
            if self.ph < 6.5:
                wqi -= min(20, (6.5 - self.ph) * 10)
            elif self.ph > 8.5:
                wqi -= min(20, (self.ph - 8.5) * 10)

        # TDS penalty (threshold: 500 ppm)
        if self.tds_ppm is not None and self.tds_ppm > 500:
            wqi -= min(30, (self.tds_ppm - 500) / 50)

        # Turbidity penalty (threshold: 5 NTU)
        if self.turbidity_ntu is not None and self.turbidity_ntu > 5:
            wqi -= min(20, (self.turbidity_ntu - 5) * 2)

        # Chlorine penalty (optimal: 0.2-5.0 mg/L)
        if self.free_chlorine_mg_l is not None:
            if self.free_chlorine_mg_l < 0.2:
                wqi -= 15
            elif self.free_chlorine_mg_l > 5.0:
                wqi -= 10

        # Coliform penalty
        if self.total_coliform_mpn is not None and self.total_coliform_mpn > 0:
            wqi -= min(25, self.total_coliform_mpn * 0.5)

        # Return comprehensive result
        return {
            'wqi_score': max(0, min(100, wqi)),
            **coverage  # Unpack all coverage metrics
        }

    def get_wqi_class(self):
        """Get WQI compliance class with data quality warnings"""
        wqi_result = self.calculate_wqi()

        # Check data sufficiency
        if not wqi_result['has_sufficient_data']:
            if wqi_result['data_quality_tier'] == 'insufficient':
                return 'Insufficient Data', 'Cannot assess - no key parameters measured'
            else:  # partial
                coverage = wqi_result['data_coverage_pct']
                return 'Partial Assessment', f'Limited reliability - {coverage:.0f}% coverage'

        # Normal classification
        wqi = wqi_result['wqi_score']
        if wqi >= 90:
            return 'Excellent', 'Safe to drink'
        elif wqi >= 70:
            return 'Compliant', 'Safe with minor treatment'
        elif wqi >= 50:
            return 'Warning', 'Treatment required'
        else:
            return 'Unsafe', 'Not safe for consumption'

    def __repr__(self):
        return f'<TestResult {self.id} for Sample {self.sample_id}>'
