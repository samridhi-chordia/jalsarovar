"""
Jal Sarovar Application Entry Point
Water Quality Testing and Analysis System
"""
from app import create_app, db
from app.models.user import User
from app.models.site import Site
from app.models.water_sample import WaterSample
from app.models.test_result import TestResult
from app.models.analysis import Analysis

# Create Flask application instance
app = create_app()

# Flask shell context
@app.shell_context_processor
def make_shell_context():
    """Make database and models available in flask shell"""
    return {
        'db': db,
        'User': User,
        'Site': Site,
        'WaterSample': WaterSample,
        'TestResult': TestResult,
        'Analysis': Analysis
    }

if __name__ == '__main__':
    # Run development server
    app.run(
        host='0.0.0.0',
        port=5050,
        debug=True
    )
