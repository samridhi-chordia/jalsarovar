"""SEO Configuration for Jal Sarovar
Meta tags, keywords, descriptions, and structured data for all pages
"""

# Base SEO Information
SITE_NAME = "Jal Sarovar"
SITE_TAGLINE = "ML-Driven Water Quality Monitoring System"
SITE_URL = "https://jalsarovar.com"
SITE_AUTHOR = "Samridhi Chordia"
SITE_KEYWORDS_BASE = "water quality monitoring, India water testing, Amrit Sarovar, water quality analysis, ML water monitoring, IoT water sensors, water contamination detection, Jal Jeevan Mission, water safety India, drinking water quality"

# Page-specific SEO configurations
SEO_CONFIG = {
    'dashboard': {
        'title': 'Dashboard - Jal Sarovar | Real-Time Water Quality Monitoring',
        'description': 'Monitor water quality across India in real-time. Track contamination levels, analyze trends, and ensure safe drinking water with ML-powered water quality monitoring system.',
        'keywords': 'water quality dashboard, real-time water monitoring, water contamination tracking, India water quality, water safety dashboard, drinking water monitoring',
        'og_type': 'website'
    },
    'sites': {
        'title': 'Water Monitoring Sites - Jal Sarovar | 68,000+ Water Bodies Across India',
        'description': 'Comprehensive database of water monitoring sites across India supporting Mission Amrit Sarovar. Track water quality at 68,000+ water bodies including ponds, lakes, tanks, and reservoirs.',
        'keywords': 'water monitoring sites India, Amrit Sarovar water bodies, water quality sites, India water sources, monitoring locations, public water bodies India',
        'og_type': 'website'
    },
    'samples': {
        'title': 'Water Quality Samples - Jal Sarovar | Laboratory Testing & Analysis',
        'description': 'Access comprehensive water quality test results and laboratory analysis. Track 40+ water quality parameters including pH, TDS, contamination levels, and WHO compliance.',
        'keywords': 'water quality testing, water sample analysis, laboratory water testing, water quality parameters, WHO water standards, BIS water standards, water testing results',
        'og_type': 'website'
    },
    'analysis': {
        'title': 'Water Quality Analysis - Jal Sarovar | ML-Powered Contamination Detection',
        'description': 'AI-powered water quality analysis with 92% accuracy. Detect contamination types, predict water safety, and get treatment recommendations using machine learning.',
        'keywords': 'water quality analysis, ML water analysis, contamination detection, water safety prediction, AI water testing, XGBoost water quality, water treatment recommendations',
        'og_type': 'website'
    },
    'wqi_calculator': {
        'title': 'WQI Calculator - Jal Sarovar | Water Quality Index Calculator',
        'description': 'Calculate Water Quality Index (WQI) instantly. Free online tool to assess drinking water safety based on WHO and BIS standards. Check water quality parameters compliance.',
        'keywords': 'WQI calculator, water quality index, water quality calculator, WHO water standards, BIS water standards, drinking water quality assessment, water safety calculator',
        'og_type': 'website'
    },
    'about': {
        'title': 'About Jal Sarovar | ML-Based Water Quality Monitoring for India',
        'description': 'Learn about India\'s first ML-based water quality monitoring system. Supporting Mission Amrit Sarovar, Jal Jeevan Mission, and ensuring safe drinking water across India with 92% ML accuracy.',
        'keywords': 'about Jal Sarovar, water quality monitoring India, Mission Amrit Sarovar, Jal Jeevan Mission, water safety India, ML water monitoring, water quality research',
        'og_type': 'website'
    },
    'portfolio_home': {
        'title': 'Samridhi Chordia | Student, Researcher & ML Developer',
        'description': 'Portfolio of Samridhi Chordia - Y Combinator AI Startup School participant, Johns Hopkins researcher, and founder of Jal Sarovar water quality monitoring system.',
        'keywords': 'Samridhi Chordia, Y Combinator, Johns Hopkins research, ML developer, water quality research, AI student, STEM researcher India',
        'og_type': 'profile'
    },
    'portfolio_bio': {
        'title': 'About Samridhi Chordia | Researcher & Founder of Jal Sarovar',
        'description': 'Learn about Samridhi Chordia - Selected from 16,000+ applicants for Y Combinator AI Startup School, conducted research at Johns Hopkins and IIT Madras, founder of Jal Sarovar.',
        'keywords': 'Samridhi Chordia bio, Y Combinator student, Johns Hopkins researcher, IIT Madras, ML researcher India, water quality researcher',
        'og_type': 'profile'
    },
    'portfolio_projects': {
        'title': 'Projects - Samridhi Chordia | ML & Research Portfolio',
        'description': 'Explore ML and research projects including Jal Sarovar (water quality monitoring), LEGOLAS (solar cell optimization), and mental health technology.',
        'keywords': 'ML projects, research projects, water quality projects, solar cell optimization, AI projects India, student research projects',
        'og_type': 'website'
    },
    'portfolio_contact': {
        'title': 'Contact Samridhi Chordia | Collaboration Opportunities',
        'description': 'Get in touch for collaboration on ML projects, research opportunities, educational technology, and social impact initiatives.',
        'keywords': 'contact Samridhi Chordia, ML collaboration, research collaboration, STEM projects, social impact technology',
        'og_type': 'website'
    }
}

# Schema.org Structured Data Templates
SCHEMA_ORGANIZATION = {
    "@context": "https://schema.org",
    "@type": "Organization",
    "name": "Jal Sarovar",
    "description": "ML-Driven Water Quality Monitoring System for India",
    "url": "https://jalsarovar.com",
    "logo": "https://jalsarovar.com/static/images/logo.png",
    "founder": {
        "@type": "Person",
        "name": "Samridhi Chordia",
        "url": "https://jalsarovar.com/samridhi-chordia/"
    },
    "foundingDate": "2024",
    "address": {
        "@type": "PostalAddress",
        "addressCountry": "IN"
    },
    "sameAs": [
        "https://github.com/samridhi-chordia"
    ]
}

SCHEMA_WEB_APPLICATION = {
    "@context": "https://schema.org",
    "@type": "WebApplication",
    "name": "Jal Sarovar Water Quality Monitoring System",
    "applicationCategory": "UtilitiesApplication",
    "operatingSystem": "Web",
    "offers": {
        "@type": "Offer",
        "price": "0",
        "priceCurrency": "INR"
    },
    "description": "ML-powered water quality monitoring system supporting India's Mission Amrit Sarovar and Jal Jeevan Mission",
    "featureList": [
        "Real-time water quality monitoring",
        "ML-based contamination detection",
        "WQI calculation",
        "Water safety predictions",
        "Treatment recommendations"
    ]
}

SCHEMA_RESEARCH = {
    "@context": "https://schema.org",
    "@type": "ResearchProject",
    "name": "Jal Sarovar: ML-Driven Water Quality Monitoring",
    "description": "Comprehensive machine learning framework for water quality monitoring in India with 92% accuracy",
    "keywords": "water quality, machine learning, India, contamination detection, water safety",
    "about": {
        "@type": "Thing",
        "name": "Water Quality Monitoring",
        "description": "Ensuring safe drinking water through ML-powered analysis"
    }
}

def get_seo_data(page_key):
    """Get SEO data for a specific page"""
    return SEO_CONFIG.get(page_key, {
        'title': f'{SITE_NAME} - {SITE_TAGLINE}',
        'description': 'ML-driven water quality monitoring system for India supporting Mission Amrit Sarovar and Jal Jeevan Mission.',
        'keywords': SITE_KEYWORDS_BASE,
        'og_type': 'website'
    })
