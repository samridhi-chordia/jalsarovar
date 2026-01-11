"""
Data Processor Service
Handles data transformation, validation, and pipeline orchestration
"""
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from app import db
from app.models import (
    Site, WaterSample, TestResult, Analysis,
    SiteRiskPrediction, ContaminationPrediction,
    WaterQualityForecast, WQIReading, AnomalyDetection,
    CostOptimizationResult, SensorReading
)
from app.services.contamination_analyzer import ContaminationAnalyzer
from app.services.ml_pipeline import MLPipeline


class DataProcessor:
    """
    Orchestrates data flow between database and ML models
    Handles the complete pipeline from data input to analysis
    """

    def __init__(self):
        self.analyzer = ContaminationAnalyzer()
        self.ml_pipeline = None  # Lazy load

    def get_ml_pipeline(self):
        """Lazy load ML pipeline"""
        if self.ml_pipeline is None:
            self.ml_pipeline = MLPipeline()
        return self.ml_pipeline

    # ========== Sample Processing Pipeline ==========

    def process_new_sample(self, sample_id: int) -> Dict:
        """
        Complete processing pipeline for a new water sample

        1. Get sample and test results
        2. Run contamination analysis
        3. Run ML classification
        4. Update site risk assessment
        5. Generate forecasts
        6. Store all results

        Returns:
            Processing results summary
        """
        sample = WaterSample.query.get(sample_id)
        if not sample:
            return {'error': 'Sample not found'}

        test_result = sample.get_latest_test()
        if not test_result:
            return {'error': 'No test results for sample'}

        site = sample.site
        results = {
            'sample_id': sample_id,
            'site_id': site.id,
            'processed_at': datetime.utcnow().isoformat()
        }

        # 1. Run rule-based contamination analysis
        analysis_result = self.analyzer.analyze(test_result, sample, site)
        analysis = self._save_analysis(sample, test_result, analysis_result)
        results['analysis_id'] = analysis.id
        results['contamination_type'] = analysis_result['contamination_type']
        results['severity'] = analysis_result['severity_level']

        # 2. Run ML contamination classification
        ml = self.get_ml_pipeline()
        ml_classification = ml.classify_contamination(test_result, sample, site)
        contamination_pred = self._save_contamination_prediction(sample, analysis, ml_classification)
        results['ml_prediction'] = ml_classification['predicted_type']

        # 3. Update site risk assessment
        site_risk = self._update_site_risk(site)
        results['site_risk'] = site_risk['risk_level']

        # 4. Update sample status
        sample.status = 'analyzed'
        db.session.commit()

        return results

    def _save_analysis(self, sample: WaterSample, test_result: TestResult,
                       analysis_result: Dict) -> Analysis:
        """Save analysis result to database"""
        analysis = Analysis(
            sample_id=sample.id,
            test_result_id=test_result.id,
            is_contaminated=analysis_result['is_contaminated'],
            contamination_type=analysis_result['contamination_type_key'],
            severity_level=analysis_result['severity_level'],
            confidence_score=analysis_result['confidence_score'],
            wqi_score=analysis_result['wqi_score'],
            wqi_class=analysis_result['wqi_class'],
            data_coverage_pct=analysis_result.get('data_coverage_pct'),
            parameters_measured=analysis_result.get('parameters_measured'),
            key_parameters_measured=analysis_result.get('key_parameters_measured'),
            has_sufficient_data=analysis_result.get('has_sufficient_data', True),
            data_quality_tier=analysis_result.get('data_quality_tier', 'full'),
            runoff_sediment_score=analysis_result['runoff_sediment_score'],
            sewage_ingress_score=analysis_result['sewage_ingress_score'],
            salt_intrusion_score=analysis_result['salt_intrusion_score'],
            pipe_corrosion_score=analysis_result['pipe_corrosion_score'],
            disinfectant_decay_score=analysis_result['disinfectant_decay_score'],
            is_compliant_who=analysis_result['is_compliant_who'],
            is_compliant_bis=analysis_result['is_compliant_bis'],
            who_violations=analysis_result['who_violations'],
            bis_violations=analysis_result['bis_violations'],
            primary_recommendation=analysis_result['primary_recommendation'],
            secondary_recommendations=analysis_result['secondary_recommendations'],
            estimated_treatment_cost_inr=analysis_result['estimated_treatment_cost_inr'],
            treatment_urgency=analysis_result['treatment_urgency'],
            analysis_method=analysis_result['analysis_method'],
            analysis_date=analysis_result['analysis_date']
        )
        db.session.add(analysis)
        db.session.commit()
        return analysis

    def _save_contamination_prediction(self, sample: WaterSample, analysis: Analysis,
                                        prediction: Dict) -> ContaminationPrediction:
        """Save ML contamination prediction"""
        pred = ContaminationPrediction(
            sample_id=sample.id,
            analysis_id=analysis.id,
            predicted_type=prediction['predicted_type'],
            confidence=prediction['confidence'],
            prob_runoff_sediment=prediction['prob_runoff_sediment'],
            prob_sewage_ingress=prediction['prob_sewage_ingress'],
            prob_salt_intrusion=prediction['prob_salt_intrusion'],
            prob_pipe_corrosion=prediction['prob_pipe_corrosion'],
            prob_disinfectant_decay=prediction['prob_disinfectant_decay'],
            shap_explanations=prediction['shap_explanations'],
            model_version=prediction['model_version'],
            f1_score=prediction['f1_score']
        )
        db.session.add(pred)
        db.session.commit()
        return pred

    # ========== Site Risk Processing ==========

    def _update_site_risk(self, site: Site) -> Dict:
        """Update site risk assessment"""
        # Get site features for prediction
        features = self._extract_site_features(site)

        # Get ML prediction
        ml = self.get_ml_pipeline()
        risk_result = ml.predict_site_risk(features)

        # Save prediction
        prediction = SiteRiskPrediction(
            site_id=site.id,
            risk_level=risk_result['risk_level'],
            risk_score=risk_result['risk_score'],
            confidence=risk_result['confidence'],
            prob_critical=risk_result['prob_critical'],
            prob_high=risk_result['prob_high'],
            prob_medium=risk_result['prob_medium'],
            prob_low=risk_result['prob_low'],
            top_features=risk_result['top_features'],
            recommended_frequency=risk_result['recommended_frequency'],
            tests_per_year=risk_result['tests_per_year'],
            model_version=risk_result['model_version']
        )
        db.session.add(prediction)

        # Update site with latest risk
        site.current_risk_level = risk_result['risk_level']
        site.risk_score = risk_result['risk_score']
        site.last_risk_assessment = datetime.utcnow()
        site.testing_frequency = risk_result['recommended_frequency']

        db.session.commit()

        return risk_result

    def _extract_site_features(self, site: Site) -> Dict:
        """Extract features for site risk prediction"""
        # Calculate 30-day contamination rate
        contamination_rate = site.get_contamination_rate(days=30)

        # Days since last test
        days_since_test = 30  # Default
        if site.last_tested:
            days_since_test = (datetime.utcnow() - site.last_tested).days

        return {
            'site_type': site.site_type,
            'is_coastal': site.is_coastal,
            'is_industrial_nearby': site.is_industrial_nearby,
            'is_agricultural_nearby': site.is_agricultural_nearby,
            'is_urban': site.is_urban,
            'population_served': site.population_served or 0,
            'contamination_rate_30d': contamination_rate,
            'days_since_last_test': days_since_test
        }

    # ========== IoT Sensor Processing ==========

    def process_sensor_reading(self, reading: SensorReading) -> Dict:
        """
        Process real-time IoT sensor reading

        1. Calculate WQI
        2. Check for anomalies
        3. Generate alerts if needed
        """
        ml = self.get_ml_pipeline()
        results = {'reading_id': reading.id}

        # Prepare sensor data
        sensor_data = {
            'ph': reading.ph,
            'tds': reading.tds_ppm,
            'turbidity': reading.turbidity_ntu,
            'chlorine': reading.free_chlorine_mg_l,
            'temperature': reading.temperature_celsius
        }

        # 1. Calculate WQI
        wqi_result = ml.calculate_realtime_wqi(sensor_data)

        # Save WQI reading
        wqi = WQIReading(
            site_id=reading.site_id,
            sensor_id=reading.sensor_id,
            wqi_score=wqi_result['wqi_score'],
            wqi_class=wqi_result['wqi_class'],
            ph_penalty=wqi_result['ph_penalty'],
            tds_penalty=wqi_result['tds_penalty'],
            turbidity_penalty=wqi_result['turbidity_penalty'],
            chlorine_penalty=wqi_result['chlorine_penalty'],
            temperature_penalty=wqi_result['temperature_penalty'],
            ph_value=wqi_result['ph_value'],
            tds_value=wqi_result['tds_value'],
            turbidity_value=wqi_result['turbidity_value'],
            chlorine_value=wqi_result['chlorine_value'],
            temperature_value=wqi_result['temperature_value'],
            is_drinkable=wqi_result['is_drinkable']
        )
        db.session.add(wqi)
        results['wqi'] = wqi_result

        # 2. Check for anomalies
        historical_stats = self._get_sensor_stats(reading.sensor_id)
        anomaly_result = ml.detect_anomaly(sensor_data, historical_stats)

        if anomaly_result['is_anomaly']:
            anomaly = AnomalyDetection(
                site_id=reading.site_id,
                sensor_id=reading.sensor_id,
                is_anomaly=True,
                anomaly_type=anomaly_result['anomaly_type'],
                anomaly_score=anomaly_result['anomaly_score'],
                cusum_value=anomaly_result['cusum_value'],
                parameter=anomaly_result['parameter'],
                observed_value=anomaly_result['observed_value'],
                expected_value=anomaly_result['expected_value'],
                deviation_sigma=anomaly_result['deviation_sigma'],
                detection_method=anomaly_result['detection_method'],
                model_version=anomaly_result['model_version']
            )
            db.session.add(anomaly)
            results['anomaly'] = anomaly_result

        # Update reading as processed
        reading.is_processed = True
        reading.processed_at = datetime.utcnow()
        reading.wqi_calculated = True
        reading.anomaly_checked = True

        db.session.commit()

        return results

    def _get_sensor_stats(self, sensor_id: int, days: int = 30) -> Dict:
        """Get historical statistics for a sensor"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        readings = SensorReading.query.filter(
            SensorReading.sensor_id == sensor_id,
            SensorReading.reading_timestamp >= cutoff,
            SensorReading.is_valid == True
        ).all()

        stats = {}
        for param in ['ph', 'tds_ppm', 'turbidity_ntu', 'free_chlorine_mg_l', 'temperature_celsius']:
            values = [getattr(r, param) for r in readings if getattr(r, param) is not None]
            if values:
                import numpy as np
                key = param.replace('_ppm', '').replace('_ntu', '').replace('_mg_l', '').replace('_celsius', '')
                if key == 'tds_ppm':
                    key = 'tds'
                elif key == 'turbidity_ntu':
                    key = 'turbidity'
                elif key == 'free_chlorine_mg_l':
                    key = 'chlorine'
                elif key == 'temperature_celsius':
                    key = 'temperature'
                stats[key] = {
                    'mean': float(np.mean(values)),
                    'std': float(np.std(values)) if len(values) > 1 else 1.0
                }

        return stats

    # ========== Cost Optimization ==========

    def run_cost_optimization(self, budget_inr: float = None) -> Dict:
        """Run cost optimization for all active sites"""
        sites = Site.query.filter_by(is_active=True).all()

        site_data = [{
            'id': s.id,
            'name': s.site_name,
            'risk_score': s.risk_score or 50,
            'site_type': s.site_type
        } for s in sites]

        ml = self.get_ml_pipeline()
        results = ml.optimize_testing_schedule(site_data, budget_inr or 10000000)

        # Save results
        run_id = results['optimization_run_id']
        for site_result in results['site_results']:
            opt = CostOptimizationResult(
                site_id=site_result['site_id'],
                optimization_run_id=run_id,
                risk_category=site_result['risk_category'],
                current_tests_per_year=site_result['current_tests_per_year'],
                optimized_tests_per_year=site_result['optimized_tests_per_year'],
                current_cost_inr=site_result['current_cost_inr'],
                optimized_cost_inr=site_result['optimized_cost_inr'],
                cost_savings_inr=site_result['cost_savings_inr'],
                cost_reduction_percent=site_result['cost_reduction_percent'],
                detection_rate=site_result['detection_rate'],
                recommended_frequency=site_result['recommended_frequency'],
                priority_rank=site_result['priority_rank'],
                model_version=results['model_version']
            )
            db.session.add(opt)

        db.session.commit()

        return results

    # ========== Forecasting ==========

    def generate_forecasts(self, site_id: int, parameters: List[str] = None,
                           days_ahead: int = 90) -> Dict:
        """Generate water quality forecasts for a site"""
        if parameters is None:
            parameters = ['ph', 'turbidity', 'tds', 'chlorine']

        results = {'site_id': site_id, 'forecasts': {}}

        for param in parameters:
            # Get historical data
            historical = self._get_historical_parameter_data(site_id, param)

            if historical:
                ml = self.get_ml_pipeline()
                forecasts = ml.forecast_water_quality(site_id, param, historical, days_ahead)

                # Save forecasts
                for fc in forecasts[:30]:  # Save first 30 days
                    forecast = WaterQualityForecast(
                        site_id=site_id,
                        forecast_date=fc['forecast_date'],
                        parameter=param,
                        predicted_value=fc['predicted_value'],
                        lower_bound_95=fc['lower_bound_95'],
                        upper_bound_95=fc['upper_bound_95'],
                        uncertainty=fc['uncertainty'],
                        prob_exceed_threshold=fc['prob_exceed_threshold'],
                        threshold_value=fc['threshold_value'],
                        days_until_exceedance=fc['days_until_exceedance'],
                        model_version=fc['model_version'],
                        r2_score=fc['r2_score']
                    )
                    db.session.add(forecast)

                results['forecasts'][param] = forecasts[:7]  # Return first 7 days

        db.session.commit()
        return results

    def _get_historical_parameter_data(self, site_id: int, parameter: str,
                                        days: int = 365) -> List[Dict]:
        """Get historical data for a parameter"""
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Map parameter names to test result columns
        param_map = {
            'ph': 'ph',
            'turbidity': 'turbidity_ntu',
            'tds': 'tds_ppm',
            'chlorine': 'free_chlorine_mg_l'
        }
        column = param_map.get(parameter, parameter)

        samples = WaterSample.query.filter(
            WaterSample.site_id == site_id,
            WaterSample.collection_date >= cutoff.date()
        ).order_by(WaterSample.collection_date).all()

        data = []
        for sample in samples:
            test = sample.get_latest_test()
            if test:
                value = getattr(test, column, None)
                if value is not None:
                    data.append({
                        'date': sample.collection_date,
                        'value': float(value)
                    })

        return data
