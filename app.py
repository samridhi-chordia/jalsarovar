#!/usr/bin/env python
"""
Jal Sarovar - Amrit Sarovar Water Quality Management System
Main Application Entry Point
"""
import os
from app import create_app, db

# Create application
app = create_app(os.environ.get('FLASK_ENV', 'development'))


@app.shell_context_processor
def make_shell_context():
    """Make shell context for flask shell"""
    from app.models import (
        User, Site, WaterSample, TestResult, Analysis,
        TreatmentMethod, Intervention, IoTSensor, SensorReading,
        SiteRiskPrediction, ContaminationPrediction, WQIReading
    )
    return {
        'db': db,
        'User': User,
        'Site': Site,
        'WaterSample': WaterSample,
        'TestResult': TestResult,
        'Analysis': Analysis,
        'TreatmentMethod': TreatmentMethod,
        'Intervention': Intervention,
        'IoTSensor': IoTSensor,
        'SensorReading': SensorReading,
        'SiteRiskPrediction': SiteRiskPrediction,
        'ContaminationPrediction': ContaminationPrediction,
        'WQIReading': WQIReading
    }


@app.cli.command()
def init_db():
    """Initialize the database."""
    db.create_all()
    print("Database initialized!")


@app.cli.command()
def populate():
    """Populate database with test data."""
    from scripts.populate_data import main
    main()


@app.cli.command()
def recalculate_validations():
    """Recalculate validation results for all eligible sites (2+ years of data)."""
    import click
    from app.controllers.reports_validation_cache import recalculate_all_validation_results

    click.echo("Starting validation result calculation for all sites...")
    click.echo("This may take several minutes depending on the number of sites.\n")

    # Create database tables if not exist (for ValidationResult model)
    db.create_all()

    results = recalculate_all_validation_results(force_recalculate=True)

    click.echo(f"\n{'='*60}")
    click.echo("Validation calculation complete!")
    click.echo(f"Total sites processed: {results['total_sites']}")
    click.echo(f"Successfully calculated: {results['calculated']}")
    click.echo(f"Skipped (insufficient data): {results['skipped']}")
    click.echo(f"Errors: {results['errors']}")
    click.echo(f"Total time: {results['total_duration']:.2f} seconds")
    click.echo(f"{'='*60}\n")

    if results['calculated'] > 0:
        click.echo(f"✓ {results['calculated']} validation results are now cached!")
        click.echo("The /reports/validation-summary page will now load much faster.")
    else:
        click.echo("No validation results were calculated. Check that sites have 2+ years of data.")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5002, debug=True)
