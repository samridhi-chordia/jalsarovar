"""
Validation Results Caching Service
Calculates and stores pre-computed validation metrics for performance
"""
from datetime import datetime, timedelta
import time
import numpy as np
from app import db
from app.models import (
    Site, WaterSample, TestResult, ValidationResult
)
from app.controllers.reports import (
    validate_site_with_2year_split
)


def calculate_and_store_validation_result(site_id, force_recalculate=False):
    """
    Calculate validation metrics for a site and store in database

    Args:
        site_id: ID of the site to validate
        force_recalculate: If True, recalculate even if recent result exists

    Returns:
        ValidationResult object or None if site not eligible
    """
    start_time = time.time()

    try:
        site = Site.query.get(site_id)
        if not site or not site.is_active:
            return None

        # Check if recent validation exists (less than 7 days old)
        if not force_recalculate:
            recent_validation = ValidationResult.query.filter_by(
                site_id=site_id,
                is_valid=True
            ).order_by(ValidationResult.calculated_at.desc()).first()

            if recent_validation:
                age_days = (datetime.utcnow() - recent_validation.calculated_at).days
                if age_days < 7:
                    print(f"Site {site_id}: Using cached validation from {age_days} days ago")
                    return recent_validation

        # Get all samples for this site
        samples = WaterSample.query.filter_by(site_id=site.id)\
            .order_by(WaterSample.collection_date).all()

        if len(samples) < 10:
            print(f"Site {site_id}: Insufficient samples ({len(samples)} < 10)")
            return None

        # Check if site has 2+ years of data
        first_sample = samples[0]
        last_sample = samples[-1]
        data_span_days = (last_sample.collection_date - first_sample.collection_date).days

        if data_span_days < 730:  # Less than 2 years
            print(f"Site {site_id}: Insufficient data span ({data_span_days} days < 730)")
            return None

        # Split into training (first 2 years) and test (remaining)
        cutoff_date = first_sample.collection_date + timedelta(days=730)
        training_samples = [s for s in samples if s.collection_date <= cutoff_date]
        test_samples = [s for s in samples if s.collection_date > cutoff_date]

        if len(test_samples) < 5:  # Need minimum test samples
            print(f"Site {site_id}: Insufficient test samples ({len(test_samples)} < 5)")
            return None

        print(f"Site {site_id}: Calculating validation with {len(training_samples)} training, {len(test_samples)} test samples")

        # Run validation calculation
        validation_metrics = validate_site_with_2year_split(
            site, training_samples, test_samples
        )

        # Create or update ValidationResult
        validation = ValidationResult.query.filter_by(site_id=site_id).first()
        if not validation:
            validation = ValidationResult(site_id=site_id)
            db.session.add(validation)

        # Store training/test metadata (handle both date and datetime objects)
        def to_date(dt):
            """Convert datetime or date to date object"""
            return dt.date() if hasattr(dt, 'date') and callable(dt.date) else dt

        validation.training_start_date = to_date(training_samples[0].collection_date)
        validation.training_end_date = to_date(training_samples[-1].collection_date)
        validation.test_start_date = to_date(test_samples[0].collection_date)
        validation.test_end_date = to_date(test_samples[-1].collection_date)
        validation.training_samples_count = len(training_samples)
        validation.test_samples_count = len(test_samples)

        # Store WQI metrics
        if validation_metrics.get('wqi_metrics'):
            wqi = validation_metrics['wqi_metrics']
            validation.wqi_mae = wqi.get('mae')
            validation.wqi_rmse = wqi.get('rmse')
            validation.wqi_accuracy_within_10 = wqi.get('accuracy_within_10')
            validation.wqi_predictions_count = wqi.get('n_predictions')
            validation.wqi_data_points = wqi.get('data_points', [])

        # Store Contamination metrics
        if validation_metrics.get('contamination_metrics'):
            contam = validation_metrics['contamination_metrics']
            validation.contamination_accuracy = contam.get('accuracy')
            validation.contamination_precision = contam.get('precision')
            validation.contamination_recall = contam.get('recall')
            validation.contamination_f1_score = contam.get('f1_score')
            validation.contamination_predictions_count = contam.get('n_predictions')
            validation.contamination_confusion_matrix = contam.get('confusion_matrix', {})

        # Store Risk metrics
        if validation_metrics.get('risk_metrics'):
            risk = validation_metrics['risk_metrics']
            validation.risk_accuracy = risk.get('accuracy')
            validation.risk_predictions_count = risk.get('n_predictions')
            validation.risk_confusion_matrix = risk.get('confusion_matrix', {})

        # Store Forecast metrics
        if validation_metrics.get('forecast_metrics'):
            forecast = validation_metrics['forecast_metrics']

            if forecast.get('ph'):
                validation.forecast_ph_r2 = forecast['ph'].get('r2')
                validation.forecast_ph_mae = forecast['ph'].get('mae')
                validation.forecast_ph_predictions_count = forecast['ph'].get('n_predictions')

            if forecast.get('turbidity'):
                validation.forecast_turbidity_r2 = forecast['turbidity'].get('r2')
                validation.forecast_turbidity_mae = forecast['turbidity'].get('mae')
                validation.forecast_turbidity_predictions_count = forecast['turbidity'].get('n_predictions')

            if forecast.get('tds'):
                validation.forecast_tds_r2 = forecast['tds'].get('r2')
                validation.forecast_tds_mae = forecast['tds'].get('mae')
                validation.forecast_tds_predictions_count = forecast['tds'].get('n_predictions')

            if forecast.get('temperature'):
                validation.forecast_temperature_r2 = forecast['temperature'].get('r2')
                validation.forecast_temperature_mae = forecast['temperature'].get('mae')
                validation.forecast_temperature_predictions_count = forecast['temperature'].get('n_predictions')

            # Calculate average R2
            r2_values = []
            for param in ['ph', 'turbidity', 'tds', 'temperature']:
                if forecast.get(param) and forecast[param].get('r2') is not None:
                    r2_values.append(forecast[param]['r2'])

            if r2_values:
                validation.forecast_avg_r2 = np.mean(r2_values)
                validation.forecast_total_predictions = sum(
                    forecast.get(p, {}).get('n_predictions', 0)
                    for p in ['ph', 'turbidity', 'tds', 'temperature']
                )

        # Store calculation metadata
        validation.calculated_at = datetime.utcnow()
        validation.calculation_duration_seconds = time.time() - start_time
        validation.is_valid = True
        validation.error_message = None

        db.session.commit()

        print(f"Site {site_id}: Validation calculated and stored in {validation.calculation_duration_seconds:.2f}s")
        return validation

    except Exception as e:
        db.session.rollback()
        print(f"Site {site_id}: Error calculating validation: {str(e)}")

        # Store error in database
        validation = ValidationResult.query.filter_by(site_id=site_id).first()
        if not validation:
            validation = ValidationResult(site_id=site_id)
            db.session.add(validation)

        validation.calculated_at = datetime.utcnow()
        validation.calculation_duration_seconds = time.time() - start_time
        validation.is_valid = False
        validation.error_message = str(e)[:500]  # Limit error message length

        try:
            db.session.commit()
        except:
            db.session.rollback()

        return None


def recalculate_all_validation_results(country=None, category=None, force_recalculate=False):
    """
    Batch calculate validation results for all eligible sites

    Args:
        country: Filter by country ('India', 'USA', etc.) or None for all
        category: Filter by category ('public', 'residential') or None for all
        force_recalculate: If True, recalculate even if recent results exist

    Returns:
        dict with summary statistics
    """
    start_time = time.time()

    # Build query
    query = Site.query.filter(Site.is_active == True)

    if country:
        query = query.filter(Site.country == country)

    if category == 'public':
        query = query.filter((Site.site_category == 'public') | (Site.site_category == None))
    elif category == 'residential':
        query = query.filter(Site.site_category == 'residential')

    sites = query.all()

    print(f"Starting validation calculation for {len(sites)} sites...")

    results = {
        'total_sites': len(sites),
        'calculated': 0,
        'skipped': 0,
        'errors': 0,
        'total_duration': 0
    }

    for i, site in enumerate(sites, 1):
        print(f"\n[{i}/{len(sites)}] Processing site {site.id} ({site.site_name})...")

        validation = calculate_and_store_validation_result(
            site.id,
            force_recalculate=force_recalculate
        )

        if validation and validation.is_valid:
            results['calculated'] += 1
        elif validation and not validation.is_valid:
            results['errors'] += 1
        else:
            results['skipped'] += 1

    results['total_duration'] = time.time() - start_time

    print(f"\n{'='*60}")
    print(f"Validation calculation complete!")
    print(f"Total sites: {results['total_sites']}")
    print(f"Calculated: {results['calculated']}")
    print(f"Skipped: {results['skipped']}")
    print(f"Errors: {results['errors']}")
    print(f"Total time: {results['total_duration']:.2f}s")
    print(f"{'='*60}")

    return results
