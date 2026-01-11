# Jal Sarovar - Water Quality Management System

A comprehensive web-based platform for monitoring and analyzing water quality across multiple sites, built for the Amrit Sarovar Initiative.

## Overview

Jal Sarovar is a Flask-based water quality management system that combines traditional water testing with machine learning predictions to provide actionable insights for water conservation and quality improvement.

### Key Features

- **Multi-Site Management**: Monitor water quality across multiple locations
- **Water Sample Tracking**: Record and manage water samples with test results
- **ML-Based Predictions**:
  - Contamination classification (Global & India-specific models)
  - Water Quality Index (WQI) prediction
  - Site risk assessment
  - Anomaly detection
- **Trend Analysis & Forecasting**: Historical data analysis and future predictions
- **Intervention Tracking**: Monitor effectiveness of water quality interventions
- **Data Import**: Support for CPCB (Central Pollution Control Board) data
- **Role-Based Access Control**: 10-tier permission system
- **Email Notifications**: Automated alerts and verification
- **Portfolio Integration**: Built-in developer portfolio website

## Technology Stack

- **Backend**: Python 3.x, Flask 3.0.0
- **Database**: PostgreSQL with SQLAlchemy ORM
- **ML/Data Science**: scikit-learn, XGBoost, pandas, numpy, joblib
- **Authentication**: Flask-Login, Google OAuth (Authlib)
- **Email**: Flask-Mail with SMTP support
- **Caching**: Redis-based rate limiting
- **Production Server**: Gunicorn + Nginx
- **Containerization**: Docker & Docker Compose
- **Frontend**: HTML, CSS, JavaScript (vanilla)

## Project Structure

```
jalsarovar/
├── app/
│   ├── controllers/        # Flask blueprints (20 route controllers)
│   ├── models/            # SQLAlchemy ORM models (13 models)
│   ├── services/          # Business logic services
│   ├── templates/         # Jinja2 HTML templates
│   ├── static/            # CSS, JS, images, portfolio content
│   └── ml/models/         # Pre-trained ML models (8 .joblib files)
├── migrations/            # Alembic database migrations
├── deployment/            # Deployment scripts and configs
├── app.py                 # Application entry point
├── config.py              # Configuration classes
├── wsgi.py                # WSGI entry point
├── requirements.txt       # Python dependencies
├── docker-compose.yml     # Docker orchestration
├── Dockerfile             # Container image definition
└── nginx-production.conf  # Nginx reverse proxy config
```

## Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Redis (for rate limiting)
- Node.js (optional, for frontend development)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/samridhi-chordia/jalsarovar.git
   cd jalsarovar
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.production.template .env
   # Edit .env with your configuration
   ```

5. **Initialize database**
   ```bash
   flask db upgrade
   ```

6. **Run development server**
   ```bash
   python app.py
   ```

   Visit: `http://localhost:5000`

### Docker Deployment

```bash
docker-compose up -d
```

## Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Flask Configuration
SECRET_KEY=your-secret-key-here
FLASK_ENV=production

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/jalsarovar

# Email (SendGrid or SMTP)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Google OAuth
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret

# Redis
REDIS_URL=redis://localhost:6379/0
```

See [EMAIL_SETUP_GUIDE.md](EMAIL_SETUP_GUIDE.md) and [OAUTH_SETUP_GUIDE.md](OAUTH_SETUP_GUIDE.md) for detailed configuration instructions.

## Documentation

- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete deployment guide for production
- **[EMAIL_SETUP_GUIDE.md](EMAIL_SETUP_GUIDE.md)** - Email service configuration
- **[OAUTH_SETUP_GUIDE.md](OAUTH_SETUP_GUIDE.md)** - Google OAuth setup
- **[QUICK_START.md](QUICK_START.md)** - CPCB data import guide
- **[deployment/README.md](deployment/README.md)** - Deployment scripts documentation

## Machine Learning Models

The system includes 8 pre-trained ML models:

1. **Contamination Classifier** (Global & India-specific)
2. **Anomaly Detector** - Identifies unusual water quality patterns
3. **WQI Predictor** - Predicts Water Quality Index
4. **Site Risk Classifier** - Assesses contamination risk
5. **Label Encoders & Scalers** - Data preprocessing models

Models are located in `app/ml/models/` and automatically loaded on startup.

## Database Schema

Key models include:

- **User** - User accounts with role-based permissions
- **Site** - Water monitoring locations
- **WaterSample** - Water sample records
- **TestResult** - Laboratory test results
- **Analysis** - Water quality analysis
- **Intervention** - Quality improvement interventions
- **MLPrediction** - Machine learning predictions
- **IOTSensor** - IoT sensor data integration

## API Endpoints

### Authentication
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `GET /auth/oauth/google` - Google OAuth login

### Sites
- `GET /sites` - List all sites
- `POST /sites/new` - Create new site
- `GET /sites/<id>` - Site details

### Samples
- `GET /samples` - List water samples
- `POST /samples/new` - Create new sample
- `GET /samples/<id>` - Sample details

### Analytics
- `GET /analytics/dashboard` - Analytics dashboard
- `GET /analytics/trends` - Trend analysis
- `GET /analytics/forecast` - Predictions

See full API documentation in the application.

## Development

### Running Tests

```bash
pytest tests/
```

### Database Migrations

Create a new migration:
```bash
flask db migrate -m "Description of changes"
```

Apply migrations:
```bash
flask db upgrade
```

### Code Style

Follow PEP 8 guidelines. Format code with:
```bash
black .
flake8 .
```

## Production Deployment

For production deployment to cloud platforms (AWS, Azure, GCP), see [DEPLOYMENT.md](DEPLOYMENT.md).

Key steps:
1. Set up production database (PostgreSQL)
2. Configure environment variables
3. Set up Nginx reverse proxy
4. Configure SSL/TLS certificates
5. Set up email service (SendGrid recommended)
6. Configure Google OAuth
7. Run database migrations
8. Start Gunicorn workers
9. Set up monitoring and logging

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Security

- All sensitive data excluded from version control (`.env` files)
- SQL injection prevention via SQLAlchemy ORM
- XSS protection with template escaping
- CSRF protection enabled
- Rate limiting on API endpoints
- OAuth 2.0 for third-party authentication
- Password hashing with Werkzeug

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Author

**Samridhi Chordia**
- Email: samridhichordia@gmail.com
- GitHub: [@samridhi-chordia](https://github.com/samridhi-chordia)
- Website: [jalsarovar.com](https://www.jalsarovar.com)

## Acknowledgments

- Amrit Sarovar Initiative
- Central Pollution Control Board (CPCB) for data standards
- Flask and Python community
- scikit-learn and XGBoost teams

## Support

For issues, questions, or contributions:
- Open an issue on GitHub
- Email: samridhichordia@gmail.com

---

**Version**: 2.0
**Last Updated**: January 2026
