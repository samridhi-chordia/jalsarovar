#!/usr/bin/env python
"""
Jal Sarovar - Amrit Sarovar Setup Script
Complete setup for the water quality management system

Usage:
    python setup.py
"""

import os
import sys
import subprocess


def check_python():
    """Check Python version"""
    print("Checking Python version...")
    if sys.version_info < (3, 9):
        print("Error: Python 3.9+ required")
        sys.exit(1)
    print(f"  Python {sys.version_info.major}.{sys.version_info.minor} OK")


def check_postgresql():
    """Check PostgreSQL availability"""
    print("\nChecking PostgreSQL...")
    try:
        import psycopg2
        print("  psycopg2 available")
    except ImportError:
        print("  Warning: psycopg2 not installed, will install with requirements")


# def install_requirements():
#     """Install Python requirements"""
#     print("\nInstalling requirements...")
#     subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'])
#     print("  Requirements installed")


def create_database():
    """Create PostgreSQL database"""
    print("\nCreating PostgreSQL database...")
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

        # Connect to PostgreSQL server
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Create database if not exists
        cursor.execute("SELECT 1 FROM pg_database WHERE datname = 'jal_sarovar_prod'")
        if not cursor.fetchone():
            cursor.execute("CREATE DATABASE jal_sarovar_prod")
            print("  Database 'jal_sarovar_prod' created")
        else:
            print("  Database 'jal_sarovar_prod' already exists")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"  Warning: Could not create database: {e}")
        print("  Please create the database manually:")
        print("    CREATE DATABASE jal_sarovar_prod;")


def initialize_app():
    """Initialize Flask application and create tables"""
    print("\nInitializing application...")
    from app import create_app, db

    app = create_app('development')
    with app.app_context():
        db.create_all()
        print("  Database tables created")


def populate_data():
    """Run data population script"""
    print("\nPopulating database with test data...")
    from scripts.populate_data import main
    main()


def print_instructions():
    """Print usage instructions"""
    print("\n" + "="*60)
    print("SETUP COMPLETE!")
    print("="*60)
    print("\nTo start the application:")
    print("  python app.py")
    print("\nThen open: http://localhost:5000")
    print("\nLogin credentials:")
    print("  Admin:    admin / admin123")
    print("  Analyst:  analyst / analyst123")
    print("\nAPI Endpoints:")
    print("  GET  /api/ml/site-risk/<site_id>")
    print("  POST /api/ml/site-risk/<site_id>/predict")
    print("  GET  /api/ml/contamination/<sample_id>")
    print("  GET  /api/ml/wqi/<site_id>")
    print("  POST /api/ml/wqi/calculate")
    print("  GET  /api/ml/forecast/<site_id>")
    print("  GET  /api/ml/anomalies/<site_id>")
    print("  GET  /api/ml/cost-optimizer/results")
    print("  POST /api/ml/cost-optimizer/run")
    print("="*60)


def main():
    """Main setup function"""
    print("="*60)
    print("Jal Sarovar - Amrit Sarovar Water Quality System")
    print("Setup Script")
    print("="*60)

    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    check_python()
    check_postgresql()
    # install_requirements()
    create_database()
    initialize_app()
    populate_data()
    print_instructions()


if __name__ == '__main__':
    main()
