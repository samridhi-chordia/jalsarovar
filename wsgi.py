"""
WSGI entry point for Jal Sarovar application
"""
from app import create_app

# Create the Flask application
app = create_app()

if __name__ == "__main__":
    app.run()
