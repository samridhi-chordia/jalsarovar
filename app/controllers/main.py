"""Main routes - Home and landing pages"""
from flask import Blueprint, render_template, redirect, url_for, send_from_directory, current_app, Response
from flask_login import login_required, current_user
from app import db
from app.models import Site, WaterSample, Analysis
import os
from datetime import datetime

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Home page - redirects to dashboard"""
    return redirect(url_for('dashboard.index'))


@main_bp.route('/about')
def about():
    """About page"""
    return render_template('main/about.html')


@main_bp.route('/health')
def health():
    """Health check endpoint for monitoring and load balancers"""
    health_status = {
        'status': 'healthy',
        'service': 'jal-sarovar',
        'timestamp': datetime.utcnow().isoformat()
    }

    # Check database connection
    try:
        db.session.execute(db.text('SELECT 1'))
        health_status['database'] = 'connected'
    except Exception as e:
        health_status['database'] = 'error'
        health_status['status'] = 'unhealthy'

    # Check Redis connection
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379)
        r.ping()
        health_status['redis'] = 'connected'
    except Exception as e:
        health_status['redis'] = 'error'
        # Redis failure doesn't make app unhealthy, just degraded
        if health_status['status'] == 'healthy':
            health_status['status'] = 'degraded'

    # Return appropriate HTTP status code
    status_code = 200 if health_status['status'] in ['healthy', 'degraded'] else 503

    return health_status, status_code


@main_bp.route('/sitemap.xml')
def sitemap_index():
    """Generate sitemap index pointing to all sitemap files"""
    today = datetime.now().strftime('%Y-%m-%d')

    # Count recent records (last 2 years for better SEO focus)
    from dateutil.relativedelta import relativedelta
    cutoff_date = datetime.now() - relativedelta(years=2)

    sample_count = db.session.query(WaterSample).filter(WaterSample.collection_date >= cutoff_date).count()
    analysis_count = db.session.query(Analysis).filter(Analysis.analysis_date >= cutoff_date).count()

    # Calculate number of sitemaps (10k URLs per file for better performance)
    sample_sitemaps = (sample_count // 10000) + 1 if sample_count > 0 else 0
    analysis_sitemaps = (analysis_count // 10000) + 1 if analysis_count > 0 else 0

    sitemap_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap>
    <loc>https://jalsarovar.com/sitemap_static.xml</loc>
    <lastmod>{today}</lastmod>
  </sitemap>
  <sitemap>
    <loc>https://jalsarovar.com/sitemap_sites.xml</loc>
    <lastmod>{today}</lastmod>
  </sitemap>
'''

    # Add sample sitemap files (recent data)
    for i in range(1, sample_sitemaps + 1):
        sitemap_xml += f'''  <sitemap>
    <loc>https://jalsarovar.com/sitemap_samples_{i}.xml</loc>
    <lastmod>{today}</lastmod>
  </sitemap>
'''

    # Add analysis sitemap files (recent data)
    for i in range(1, analysis_sitemaps + 1):
        sitemap_xml += f'''  <sitemap>
    <loc>https://jalsarovar.com/sitemap_analyses_{i}.xml</loc>
    <lastmod>{today}</lastmod>
  </sitemap>
'''

    sitemap_xml += '</sitemapindex>'

    return Response(sitemap_xml, mimetype='application/xml')


@main_bp.route('/sitemap_static.xml')
def sitemap_static():
    """Generate sitemap for static pages"""
    today = datetime.now().strftime('%Y-%m-%d')

    sitemap_xml = f'''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://jalsarovar.com/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>https://jalsarovar.com/dashboard/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://jalsarovar.com/sites/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://jalsarovar.com/samples/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://jalsarovar.com/analysis/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://jalsarovar.com/wqi/calculator</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
  <url>
    <loc>https://jalsarovar.com/about</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.6</priority>
  </url>
  <url>
    <loc>https://jalsarovar.com/samridhi-chordia/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
  <url>
    <loc>https://jalsarovar.com/samridhi-chordia/bio</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://jalsarovar.com/samridhi-chordia/projects</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>https://jalsarovar.com/samridhi-chordia/volunteer</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
  <url>
    <loc>https://jalsarovar.com/samridhi-chordia/interests</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
  <url>
    <loc>https://jalsarovar.com/samridhi-chordia/blog</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.7</priority>
  </url>
  <url>
    <loc>https://jalsarovar.com/samridhi-chordia/contact</loc>
    <lastmod>{today}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
</urlset>'''

    return Response(sitemap_xml, mimetype='application/xml')


@main_bp.route('/sitemap_sites.xml')
def sitemap_sites():
    """Generate sitemap for all site pages"""
    sites = db.session.query(Site.id, Site.updated_at).all()

    sitemap_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
'''

    for site in sites:
        lastmod = site.updated_at.strftime('%Y-%m-%d') if site.updated_at else datetime.now().strftime('%Y-%m-%d')
        sitemap_xml += f'''  <url>
    <loc>https://jalsarovar.com/sites/{site.id}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.7</priority>
  </url>
'''

    sitemap_xml += '</urlset>'
    return Response(sitemap_xml, mimetype='application/xml')


@main_bp.route('/sitemap_samples_<int:page>.xml')
def sitemap_samples(page):
    """Generate sitemap for recent sample pages (paginated, 10k per file)"""
    from dateutil.relativedelta import relativedelta
    cutoff_date = datetime.now() - relativedelta(years=2)

    offset = (page - 1) * 10000
    samples = db.session.query(WaterSample.id, WaterSample.collection_date)\
        .filter(WaterSample.collection_date >= cutoff_date)\
        .order_by(WaterSample.collection_date.desc())\
        .offset(offset).limit(10000).all()

    sitemap_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
'''

    for sample in samples:
        lastmod = sample.collection_date.strftime('%Y-%m-%d') if sample.collection_date else datetime.now().strftime('%Y-%m-%d')
        sitemap_xml += f'''  <url>
    <loc>https://jalsarovar.com/samples/{sample.id}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.6</priority>
  </url>
'''

    sitemap_xml += '</urlset>'
    return Response(sitemap_xml, mimetype='application/xml')


@main_bp.route('/sitemap_analyses_<int:page>.xml')
def sitemap_analyses(page):
    """Generate sitemap for recent analysis pages (paginated, 10k per file)"""
    from dateutil.relativedelta import relativedelta
    cutoff_date = datetime.now() - relativedelta(years=2)

    offset = (page - 1) * 10000
    analyses = db.session.query(Analysis.id, Analysis.analysis_date)\
        .filter(Analysis.analysis_date >= cutoff_date)\
        .order_by(Analysis.analysis_date.desc())\
        .offset(offset).limit(10000).all()

    sitemap_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
'''

    for analysis in analyses:
        lastmod = analysis.analysis_date.strftime('%Y-%m-%d') if analysis.analysis_date else datetime.now().strftime('%Y-%m-%d')
        sitemap_xml += f'''  <url>
    <loc>https://jalsarovar.com/analysis/{analysis.id}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.6</priority>
  </url>
'''

    sitemap_xml += '</urlset>'
    return Response(sitemap_xml, mimetype='application/xml')


@main_bp.route('/robots.txt')
def robots():
    """Serve robots.txt for search engines"""
    app_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return send_from_directory(app_root, 'robots.txt', mimetype='text/plain')
