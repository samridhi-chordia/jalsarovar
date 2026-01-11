"""
Admin Portfolio Controller - CMS for portfolio content management
Allows admin users to manage portfolio content (projects, blog, interests, volunteer work)
through web forms without editing JSON files directly.
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from functools import wraps
import os
import json
import shutil
from datetime import datetime

admin_portfolio_bp = Blueprint('admin_portfolio', __name__)

# ============================================================================
# DECORATORS
# ============================================================================

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard.index'))
        return f(*args, **kwargs)
    return decorated_function

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_content_path(content_type, content_id, is_draft=False):
    """Get filesystem path for content JSON file"""
    base_dir = os.path.join(current_app.static_folder, 'portfolio/content')
    filename = f"{content_id}.draft.json" if is_draft else f"{content_id}.json"

    if content_type == 'blog':
        # Blog uses articles.json instead of individual files
        return os.path.join(base_dir, 'blog/articles.json')
    else:
        return os.path.join(base_dir, content_type, filename)

def get_upload_path(content_type, content_id, media_type='images'):
    """Get upload directory for content media"""
    base_dir = os.path.join(current_app.static_folder, f'portfolio/{media_type}')
    return os.path.join(base_dir, content_type, content_id)

def allowed_image_file(filename):
    """Check if image file is allowed"""
    ALLOWED = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED

def allowed_video_file(filename):
    """Check if video file is allowed"""
    ALLOWED = {'mp4', 'webm', 'mov'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED

def get_page_path(page_id, is_draft=False):
    """Get filesystem path for page JSON file"""
    base_dir = os.path.join(current_app.static_folder, 'portfolio/content/pages')
    filename = f"{page_id}.draft.json" if is_draft else f"{page_id}.json"
    return os.path.join(base_dir, filename)

def load_page_data(page_id):
    """Load page data (prefer draft if exists)"""
    draft_path = get_page_path(page_id, is_draft=True)
    published_path = get_page_path(page_id, is_draft=False)

    is_draft = False
    page_data = None

    if os.path.exists(draft_path):
        try:
            with open(draft_path) as f:
                page_data = json.load(f)
            is_draft = True
        except (IOError, json.JSONDecodeError):
            pass

    if not page_data and os.path.exists(published_path):
        try:
            with open(published_path) as f:
                page_data = json.load(f)
        except (IOError, json.JSONDecodeError):
            pass

    return page_data, is_draft

def save_page_data(page_id, data, as_draft=True):
    """Save page data as draft or published"""
    try:
        # Add metadata
        data['id'] = page_id
        data['last_updated'] = datetime.now().isoformat()

        # Get file path
        filepath = get_page_path(page_id, is_draft=as_draft)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)

        # Save JSON
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        # If publishing, remove draft
        if not as_draft:
            draft_path = get_page_path(page_id, is_draft=True)
            if os.path.exists(draft_path):
                os.remove(draft_path)

        return True
    except Exception as e:
        print(f"Error saving page {page_id}: {e}")
        return False

# ============================================================================
# DASHBOARD & NAVIGATION
# ============================================================================

@admin_portfolio_bp.route('/')
@login_required
@admin_required
def index():
    """Portfolio CMS Dashboard"""
    content_dir = os.path.join(current_app.static_folder, 'portfolio/content')

    # Count content items
    stats = {
        'projects': 0,
        'projects_drafts': 0,
        'blog': 0,
        'interests': 0,
        'volunteer': 0,
    }

    # Count projects
    projects_dir = os.path.join(content_dir, 'projects')
    if os.path.exists(projects_dir):
        stats['projects'] = len([f for f in os.listdir(projects_dir)
                                if f.endswith('.json') and not f.endswith('.draft.json')])
        stats['projects_drafts'] = len([f for f in os.listdir(projects_dir)
                                       if f.endswith('.draft.json')])

    # Count blog articles
    try:
        with open(os.path.join(content_dir, 'blog/articles.json')) as f:
            articles = json.load(f)
            stats['blog'] = len(articles.get('articles', []))
    except:
        pass

    # Count interests
    interests_dir = os.path.join(content_dir, 'interests')
    if os.path.exists(interests_dir):
        stats['interests'] = len([f for f in os.listdir(interests_dir)
                                 if f.endswith('.json') and not f.endswith('.draft.json')])

    # Count volunteer items
    volunteer_dir = os.path.join(content_dir, 'volunteer')
    if os.path.exists(volunteer_dir):
        stats['volunteer'] = len([f for f in os.listdir(volunteer_dir)
                                 if f.endswith('.json') and not f.endswith('.draft.json')])

    # Count pages
    pages_dir = os.path.join(content_dir, 'pages')
    stats['pages'] = 3  # Always 3 pages (home, bio, contact)
    stats['pages_drafts'] = 0
    if os.path.exists(pages_dir):
        stats['pages_drafts'] = len([f for f in os.listdir(pages_dir)
                                     if f.endswith('.draft.json')])

    return render_template('admin/portfolio/index.html', stats=stats)

# ============================================================================
# PROJECTS CRUD
# ============================================================================

@admin_portfolio_bp.route('/projects')
@login_required
@admin_required
def list_projects():
    """List all projects (published and drafts)"""
    projects_dir = os.path.join(current_app.static_folder, 'portfolio/content/projects')

    if not os.path.exists(projects_dir):
        os.makedirs(projects_dir, exist_ok=True)
        return render_template('admin/portfolio/projects_list.html', projects=[])

    projects = []
    seen_ids = set()

    for filename in os.listdir(projects_dir):
        if filename.endswith('.json'):
            is_draft = filename.endswith('.draft.json')
            content_id = filename.replace('.draft.json', '').replace('.json', '')

            # Skip if we've already seen this ID (prefer draft version)
            if content_id in seen_ids:
                continue
            seen_ids.add(content_id)

            try:
                # Load draft if exists, otherwise published
                draft_path = os.path.join(projects_dir, f"{content_id}.draft.json")
                published_path = os.path.join(projects_dir, f"{content_id}.json")

                if os.path.exists(draft_path):
                    with open(draft_path) as f:
                        data = json.load(f)
                    projects.append({
                        'id': content_id,
                        'title': data.get('title', 'Untitled'),
                        'category': data.get('category', ''),
                        'is_draft': True,
                        'has_published': os.path.exists(published_path)
                    })
                elif os.path.exists(published_path):
                    with open(published_path) as f:
                        data = json.load(f)
                    projects.append({
                        'id': content_id,
                        'title': data.get('title', 'Untitled'),
                        'category': data.get('category', ''),
                        'is_draft': False,
                        'has_published': True
                    })
            except Exception as e:
                print(f"Error loading project {filename}: {e}")
                continue

    # Sort by title
    projects.sort(key=lambda x: x['title'])

    return render_template('admin/portfolio/projects_list.html', projects=projects)

@admin_portfolio_bp.route('/projects/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_project():
    """Create new project"""
    if request.method == 'POST':
        return save_project(None)

    return render_template('admin/portfolio/project_form.html',
                         project=None,
                         is_draft=False,
                         content_type='projects')

@admin_portfolio_bp.route('/projects/<project_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_project(project_id):
    """Edit existing project"""
    if request.method == 'POST':
        return save_project(project_id)

    # Load project data (prefer draft if exists)
    draft_path = get_content_path('projects', project_id, is_draft=True)
    published_path = get_content_path('projects', project_id, is_draft=False)

    project_data = None
    is_draft = False

    if os.path.exists(draft_path):
        with open(draft_path) as f:
            project_data = json.load(f)
        is_draft = True
    elif os.path.exists(published_path):
        with open(published_path) as f:
            project_data = json.load(f)
    else:
        flash('Project not found', 'error')
        return redirect(url_for('admin_portfolio.list_projects'))

    return render_template('admin/portfolio/project_form.html',
                         project=project_data,
                         is_draft=is_draft,
                         content_type='projects')

def save_project(project_id):
    """Save project data (helper function)"""
    try:
        action = request.form.get('action', 'save_draft')
        is_draft = (action == 'save_draft')

        # Generate ID if new
        if not project_id:
            project_id = request.form.get('id')
            if not project_id:
                # Generate from title
                title = request.form.get('title', 'untitled')
                project_id = title.lower().replace(' ', '_')[:50]
                # Remove special characters
                project_id = ''.join(c for c in project_id if c.isalnum() or c == '_')

        # Build project data from form
        project_data = {
            'id': project_id,
            'title': request.form.get('title', ''),
            'category': request.form.get('category', ''),
            'short_description': request.form.get('short_description', ''),
            'full_description': request.form.get('full_description', ''),
            'start_date': request.form.get('start_date', ''),
            'currently_active': request.form.get('currently_active') == 'on',
            'highlights': [h.strip() for h in request.form.get('highlights', '').split('\n') if h.strip()],
            'skills': [s.strip() for s in request.form.get('skills', '').split(',') if s.strip()],
            'images': request.form.getlist('existing_images'),
            'videos': request.form.getlist('existing_videos'),
            'links': []
        }

        # Parse links (JSON array from form)
        links_json = request.form.get('links_json', '[]')
        try:
            project_data['links'] = json.loads(links_json)
        except:
            project_data['links'] = []

        # Save to file
        path = get_content_path('projects', project_id, is_draft=is_draft)
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, 'w') as f:
            json.dump(project_data, f, indent=2)

        if is_draft:
            flash(f'Project saved as draft: {project_data["title"]}', 'success')
        else:
            flash(f'Project published: {project_data["title"]}', 'success')
            # Delete draft if publishing
            draft_path = get_content_path('projects', project_id, is_draft=True)
            if os.path.exists(draft_path):
                os.remove(draft_path)

        return redirect(url_for('admin_portfolio.list_projects'))

    except Exception as e:
        flash(f'Error saving project: {str(e)}', 'error')
        return redirect(url_for('admin_portfolio.list_projects'))

@admin_portfolio_bp.route('/projects/<project_id>/publish', methods=['POST'])
@login_required
@admin_required
def publish_project(project_id):
    """Publish a draft project"""
    try:
        draft_path = get_content_path('projects', project_id, is_draft=True)
        published_path = get_content_path('projects', project_id, is_draft=False)

        if not os.path.exists(draft_path):
            flash('No draft found to publish', 'error')
            return redirect(url_for('admin_portfolio.list_projects'))

        # Copy draft to published
        shutil.copy2(draft_path, published_path)
        os.remove(draft_path)

        flash('Project published successfully!', 'success')
    except Exception as e:
        flash(f'Error publishing project: {str(e)}', 'error')

    return redirect(url_for('admin_portfolio.list_projects'))

@admin_portfolio_bp.route('/projects/<project_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_project(project_id):
    """Delete project (both draft and published versions)"""
    try:
        # Delete both draft and published versions
        for is_draft in [True, False]:
            path = get_content_path('projects', project_id, is_draft=is_draft)
            if os.path.exists(path):
                os.remove(path)

        # Delete media folder
        for media_type in ['images', 'videos']:
            media_dir = get_upload_path('projects', project_id, media_type)
            if os.path.exists(media_dir):
                shutil.rmtree(media_dir)

        flash('Project deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting project: {str(e)}', 'error')

    return redirect(url_for('admin_portfolio.list_projects'))

# ============================================================================
# INTERESTS CRUD
# ============================================================================

@admin_portfolio_bp.route('/interests')
@login_required
@admin_required
def list_interests():
    """List all interests (published and drafts)"""
    interests_dir = os.path.join(current_app.static_folder, 'portfolio/content/interests')

    if not os.path.exists(interests_dir):
        os.makedirs(interests_dir, exist_ok=True)
        return render_template('admin/portfolio/interests_list.html', interests=[])

    interests = []
    seen_ids = set()

    for filename in os.listdir(interests_dir):
        if filename.endswith('.json'):
            is_draft = filename.endswith('.draft.json')
            content_id = filename.replace('.draft.json', '').replace('.json', '')

            if content_id in seen_ids:
                continue
            seen_ids.add(content_id)

            try:
                draft_path = os.path.join(interests_dir, f"{content_id}.draft.json")
                published_path = os.path.join(interests_dir, f"{content_id}.json")

                if os.path.exists(draft_path):
                    with open(draft_path) as f:
                        data = json.load(f)
                    interests.append({
                        'id': content_id,
                        'title': data.get('title', 'Untitled'),
                        'category': data.get('category', ''),
                        'is_draft': True,
                        'has_published': os.path.exists(published_path)
                    })
                elif os.path.exists(published_path):
                    with open(published_path) as f:
                        data = json.load(f)
                    interests.append({
                        'id': content_id,
                        'title': data.get('title', 'Untitled'),
                        'category': data.get('category', ''),
                        'is_draft': False,
                        'has_published': True
                    })
            except Exception as e:
                print(f"Error loading interest {filename}: {e}")
                continue

    interests.sort(key=lambda x: x['title'])
    return render_template('admin/portfolio/interests_list.html', interests=interests)

@admin_portfolio_bp.route('/interests/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_interest():
    """Create new interest"""
    if request.method == 'POST':
        return save_interest(None)

    return render_template('admin/portfolio/interest_form.html',
                         interest=None,
                         is_draft=False,
                         content_type='interests')

@admin_portfolio_bp.route('/interests/<interest_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_interest(interest_id):
    """Edit existing interest"""
    if request.method == 'POST':
        return save_interest(interest_id)

    draft_path = get_content_path('interests', interest_id, is_draft=True)
    published_path = get_content_path('interests', interest_id, is_draft=False)

    interest_data = None
    is_draft = False

    if os.path.exists(draft_path):
        with open(draft_path) as f:
            interest_data = json.load(f)
        is_draft = True
    elif os.path.exists(published_path):
        with open(published_path) as f:
            interest_data = json.load(f)
    else:
        flash('Interest not found', 'error')
        return redirect(url_for('admin_portfolio.list_interests'))

    return render_template('admin/portfolio/interest_form.html',
                         interest=interest_data,
                         is_draft=is_draft,
                         content_type='interests')

def save_interest(interest_id):
    """Save interest data (helper function)"""
    try:
        action = request.form.get('action', 'save_draft')
        is_draft = (action == 'save_draft')

        if not interest_id:
            interest_id = request.form.get('id')
            if not interest_id:
                title = request.form.get('title', 'untitled')
                interest_id = title.lower().replace(' ', '_')[:50]
                interest_id = ''.join(c for c in interest_id if c.isalnum() or c == '_')

        interest_data = {
            'id': interest_id,
            'title': request.form.get('title', ''),
            'category': request.form.get('category', ''),
            'short_description': request.form.get('short_description', ''),
            'full_description': request.form.get('full_description', ''),
            'start_date': request.form.get('start_date', ''),
            'currently_active': request.form.get('currently_active') == 'on',
            'highlights': [h.strip() for h in request.form.get('highlights', '').split('\n') if h.strip()],
            'skills': [s.strip() for s in request.form.get('skills', '').split(',') if s.strip()],
            'images': request.form.getlist('existing_images'),
            'videos': request.form.getlist('existing_videos'),
            'links': []
        }

        links_json = request.form.get('links_json', '[]')
        try:
            interest_data['links'] = json.loads(links_json)
        except:
            interest_data['links'] = []

        path = get_content_path('interests', interest_id, is_draft=is_draft)
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, 'w') as f:
            json.dump(interest_data, f, indent=2)

        if is_draft:
            flash(f'Interest saved as draft: {interest_data["title"]}', 'success')
        else:
            flash(f'Interest published: {interest_data["title"]}', 'success')
            draft_path = get_content_path('interests', interest_id, is_draft=True)
            if os.path.exists(draft_path):
                os.remove(draft_path)

        return redirect(url_for('admin_portfolio.list_interests'))

    except Exception as e:
        flash(f'Error saving interest: {str(e)}', 'error')
        return redirect(url_for('admin_portfolio.list_interests'))

@admin_portfolio_bp.route('/interests/<interest_id>/publish', methods=['POST'])
@login_required
@admin_required
def publish_interest(interest_id):
    """Publish a draft interest"""
    try:
        draft_path = get_content_path('interests', interest_id, is_draft=True)
        published_path = get_content_path('interests', interest_id, is_draft=False)

        if not os.path.exists(draft_path):
            flash('No draft found to publish', 'error')
            return redirect(url_for('admin_portfolio.list_interests'))

        shutil.copy2(draft_path, published_path)
        os.remove(draft_path)

        flash('Interest published successfully!', 'success')
    except Exception as e:
        flash(f'Error publishing interest: {str(e)}', 'error')

    return redirect(url_for('admin_portfolio.list_interests'))

@admin_portfolio_bp.route('/interests/<interest_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_interest(interest_id):
    """Delete interest (both draft and published versions)"""
    try:
        for is_draft in [True, False]:
            path = get_content_path('interests', interest_id, is_draft=is_draft)
            if os.path.exists(path):
                os.remove(path)

        for media_type in ['images', 'videos']:
            media_dir = get_upload_path('interests', interest_id, media_type)
            if os.path.exists(media_dir):
                shutil.rmtree(media_dir)

        flash('Interest deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting interest: {str(e)}', 'error')

    return redirect(url_for('admin_portfolio.list_interests'))

# ============================================================================
# VOLUNTEER CRUD
# ============================================================================

@admin_portfolio_bp.route('/volunteer')
@login_required
@admin_required
def list_volunteer():
    """List all volunteer work (published and drafts)"""
    volunteer_dir = os.path.join(current_app.static_folder, 'portfolio/content/volunteer')

    if not os.path.exists(volunteer_dir):
        os.makedirs(volunteer_dir, exist_ok=True)
        return render_template('admin/portfolio/volunteer_list.html', volunteer=[])

    volunteer = []
    seen_ids = set()

    for filename in os.listdir(volunteer_dir):
        if filename.endswith('.json'):
            is_draft = filename.endswith('.draft.json')
            content_id = filename.replace('.draft.json', '').replace('.json', '')

            if content_id in seen_ids:
                continue
            seen_ids.add(content_id)

            try:
                draft_path = os.path.join(volunteer_dir, f"{content_id}.draft.json")
                published_path = os.path.join(volunteer_dir, f"{content_id}.json")

                if os.path.exists(draft_path):
                    with open(draft_path) as f:
                        data = json.load(f)
                    volunteer.append({
                        'id': content_id,
                        'title': data.get('title', 'Untitled'),
                        'category': data.get('category', ''),
                        'is_draft': True,
                        'has_published': os.path.exists(published_path)
                    })
                elif os.path.exists(published_path):
                    with open(published_path) as f:
                        data = json.load(f)
                    volunteer.append({
                        'id': content_id,
                        'title': data.get('title', 'Untitled'),
                        'category': data.get('category', ''),
                        'is_draft': False,
                        'has_published': True
                    })
            except Exception as e:
                print(f"Error loading volunteer {filename}: {e}")
                continue

    volunteer.sort(key=lambda x: x['title'])
    return render_template('admin/portfolio/volunteer_list.html', volunteer=volunteer)

@admin_portfolio_bp.route('/volunteer/new', methods=['GET', 'POST'])
@login_required
@admin_required
def new_volunteer():
    """Create new volunteer work"""
    if request.method == 'POST':
        return save_volunteer(None)

    return render_template('admin/portfolio/volunteer_form.html',
                         volunteer=None,
                         is_draft=False,
                         content_type='volunteer')

@admin_portfolio_bp.route('/volunteer/<volunteer_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_volunteer(volunteer_id):
    """Edit existing volunteer work"""
    if request.method == 'POST':
        return save_volunteer(volunteer_id)

    draft_path = get_content_path('volunteer', volunteer_id, is_draft=True)
    published_path = get_content_path('volunteer', volunteer_id, is_draft=False)

    volunteer_data = None
    is_draft = False

    if os.path.exists(draft_path):
        with open(draft_path) as f:
            volunteer_data = json.load(f)
        is_draft = True
    elif os.path.exists(published_path):
        with open(published_path) as f:
            volunteer_data = json.load(f)
    else:
        flash('Volunteer work not found', 'error')
        return redirect(url_for('admin_portfolio.list_volunteer'))

    return render_template('admin/portfolio/volunteer_form.html',
                         volunteer=volunteer_data,
                         is_draft=is_draft,
                         content_type='volunteer')

def save_volunteer(volunteer_id):
    """Save volunteer data (helper function)"""
    try:
        action = request.form.get('action', 'save_draft')
        is_draft = (action == 'save_draft')

        if not volunteer_id:
            volunteer_id = request.form.get('id')
            if not volunteer_id:
                title = request.form.get('title', 'untitled')
                volunteer_id = title.lower().replace(' ', '_')[:50]
                volunteer_id = ''.join(c for c in volunteer_id if c.isalnum() or c == '_')

        volunteer_data = {
            'id': volunteer_id,
            'title': request.form.get('title', ''),
            'category': request.form.get('category', ''),
            'short_description': request.form.get('short_description', ''),
            'full_description': request.form.get('full_description', ''),
            'start_date': request.form.get('start_date', ''),
            'currently_active': request.form.get('currently_active') == 'on',
            'highlights': [h.strip() for h in request.form.get('highlights', '').split('\n') if h.strip()],
            'skills': [s.strip() for s in request.form.get('skills', '').split(',') if s.strip()],
            'images': request.form.getlist('existing_images'),
            'videos': request.form.getlist('existing_videos'),
            'links': []
        }

        links_json = request.form.get('links_json', '[]')
        try:
            volunteer_data['links'] = json.loads(links_json)
        except:
            volunteer_data['links'] = []

        path = get_content_path('volunteer', volunteer_id, is_draft=is_draft)
        os.makedirs(os.path.dirname(path), exist_ok=True)

        with open(path, 'w') as f:
            json.dump(volunteer_data, f, indent=2)

        if is_draft:
            flash(f'Volunteer work saved as draft: {volunteer_data["title"]}', 'success')
        else:
            flash(f'Volunteer work published: {volunteer_data["title"]}', 'success')
            draft_path = get_content_path('volunteer', volunteer_id, is_draft=True)
            if os.path.exists(draft_path):
                os.remove(draft_path)

        return redirect(url_for('admin_portfolio.list_volunteer'))

    except Exception as e:
        flash(f'Error saving volunteer work: {str(e)}', 'error')
        return redirect(url_for('admin_portfolio.list_volunteer'))

@admin_portfolio_bp.route('/volunteer/<volunteer_id>/publish', methods=['POST'])
@login_required
@admin_required
def publish_volunteer(volunteer_id):
    """Publish a draft volunteer work"""
    try:
        draft_path = get_content_path('volunteer', volunteer_id, is_draft=True)
        published_path = get_content_path('volunteer', volunteer_id, is_draft=False)

        if not os.path.exists(draft_path):
            flash('No draft found to publish', 'error')
            return redirect(url_for('admin_portfolio.list_volunteer'))

        shutil.copy2(draft_path, published_path)
        os.remove(draft_path)

        flash('Volunteer work published successfully!', 'success')
    except Exception as e:
        flash(f'Error publishing volunteer work: {str(e)}', 'error')

    return redirect(url_for('admin_portfolio.list_volunteer'))

@admin_portfolio_bp.route('/volunteer/<volunteer_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_volunteer(volunteer_id):
    """Delete volunteer work (both draft and published versions)"""
    try:
        for is_draft in [True, False]:
            path = get_content_path('volunteer', volunteer_id, is_draft=is_draft)
            if os.path.exists(path):
                os.remove(path)

        for media_type in ['images', 'videos']:
            media_dir = get_upload_path('volunteer', volunteer_id, media_type)
            if os.path.exists(media_dir):
                shutil.rmtree(media_dir)

        flash('Volunteer work deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting volunteer work: {str(e)}', 'error')

    return redirect(url_for('admin_portfolio.list_volunteer'))

# ============================================================================
# PORTFOLIO PAGES MANAGEMENT
# ============================================================================

@admin_portfolio_bp.route('/pages')
@login_required
@admin_required
def list_pages():
    """List all editable portfolio pages"""
    pages_info = []

    for page_id, page_name in [('home', 'Home Page'), ('bio', 'Bio/About Page'), ('contact', 'Contact Page')]:
        draft_path = get_page_path(page_id, is_draft=True)
        published_path = get_page_path(page_id, is_draft=False)

        has_draft = os.path.exists(draft_path)
        has_published = os.path.exists(published_path)

        pages_info.append({
            'id': page_id,
            'name': page_name,
            'has_draft': has_draft,
            'has_published': has_published,
            'status': 'draft' if has_draft else ('published' if has_published else 'not_created')
        })

    return render_template('admin/portfolio/pages_list.html', pages=pages_info)

@admin_portfolio_bp.route('/pages/home/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_home_page():
    """Edit home page content"""
    if request.method == 'POST':
        # Parse form data
        data = {
            'page_type': 'home',
            'hero': {
                'name': request.form.get('hero_name', ''),
                'subtitle': request.form.get('hero_subtitle', ''),
                'description': request.form.get('hero_description', '')
            },
            'statistics': json.loads(request.form.get('statistics_json', '[]')),
            'featured_items': json.loads(request.form.get('featured_items_json', '[]')),
            'highlights': json.loads(request.form.get('highlights_json', '[]')),
            'cta': {
                'title': request.form.get('cta_title', ''),
                'subtitle': request.form.get('cta_subtitle', ''),
                'button_text': request.form.get('cta_button_text', '')
            }
        }

        # Determine action
        action = request.form.get('action', 'save_draft')
        as_draft = (action == 'save_draft')

        if save_page_data('home', data, as_draft=as_draft):
            if as_draft:
                flash('Home page saved as draft', 'success')
            else:
                flash('Home page published successfully', 'success')
        else:
            flash('Error saving home page', 'error')

        return redirect(url_for('admin_portfolio.edit_home_page'))

    # Load existing data
    page_data, is_draft = load_page_data('home')

    # Load available content items for featured section (projects, volunteer, interests)
    available_items = []

    # Load projects
    projects_dir = os.path.join(current_app.static_folder, 'portfolio/content/projects')
    if os.path.exists(projects_dir):
        for filename in os.listdir(projects_dir):
            if filename.endswith('.json') and not filename.endswith('.draft.json'):
                try:
                    with open(os.path.join(projects_dir, filename)) as f:
                        proj = json.load(f)
                        available_items.append({
                            'type': 'project',
                            'id': proj.get('id'),
                            'title': proj.get('title'),
                            'category': proj.get('category')
                        })
                except:
                    pass

    # Load volunteer work
    volunteer_dir = os.path.join(current_app.static_folder, 'portfolio/content/volunteer')
    if os.path.exists(volunteer_dir):
        for filename in os.listdir(volunteer_dir):
            if filename.endswith('.json') and not filename.endswith('.draft.json'):
                try:
                    with open(os.path.join(volunteer_dir, filename)) as f:
                        vol = json.load(f)
                        available_items.append({
                            'type': 'volunteer',
                            'id': vol.get('id'),
                            'title': vol.get('title'),
                            'category': vol.get('category', 'Volunteer Work')
                        })
                except:
                    pass

    # Load interests
    interests_dir = os.path.join(current_app.static_folder, 'portfolio/content/interests')
    if os.path.exists(interests_dir):
        for filename in os.listdir(interests_dir):
            if filename.endswith('.json') and not filename.endswith('.draft.json'):
                try:
                    with open(os.path.join(interests_dir, filename)) as f:
                        interest = json.load(f)
                        available_items.append({
                            'type': 'interest',
                            'id': interest.get('id'),
                            'title': interest.get('title'),
                            'category': interest.get('category', 'Personal Interest')
                        })
                except:
                    pass

    return render_template('admin/portfolio/page_home_form.html',
                         page=page_data,
                         is_draft=is_draft,
                         available_items=available_items)

@admin_portfolio_bp.route('/pages/bio/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_bio_page():
    """Edit bio/about page content"""
    if request.method == 'POST':
        # Parse form data
        data = {
            'page_type': 'bio',
            'hero': {
                'title': request.form.get('hero_title', ''),
                'subtitle': request.form.get('hero_subtitle', '')
            },
            'introduction': {
                'greeting': request.form.get('intro_greeting', ''),
                'paragraphs': json.loads(request.form.get('paragraphs_json', '[]'))
            },
            'education': json.loads(request.form.get('education_json', '[]')),
            'skills': [s.strip() for s in request.form.get('skills', '').split(',') if s.strip()],
            'cta': {
                'title': request.form.get('cta_title', ''),
                'subtitle': request.form.get('cta_subtitle', ''),
                'button_text': request.form.get('cta_button_text', '')
            }
        }

        # Determine action
        action = request.form.get('action', 'save_draft')
        as_draft = (action == 'save_draft')

        if save_page_data('bio', data, as_draft=as_draft):
            if as_draft:
                flash('Bio page saved as draft', 'success')
            else:
                flash('Bio page published successfully', 'success')
        else:
            flash('Error saving bio page', 'error')

        return redirect(url_for('admin_portfolio.edit_bio_page'))

    # Load existing data
    page_data, is_draft = load_page_data('bio')

    return render_template('admin/portfolio/page_bio_form.html',
                         page=page_data,
                         is_draft=is_draft)

@admin_portfolio_bp.route('/pages/contact/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_contact_page():
    """Edit contact page content"""
    if request.method == 'POST':
        # Parse form data
        data = {
            'page_type': 'contact',
            'hero': {
                'title': request.form.get('hero_title', ''),
                'subtitle': request.form.get('hero_subtitle', '')
            },
            'intro': {
                'heading': request.form.get('intro_heading', ''),
                'text': request.form.get('intro_text', '')
            },
            'interest_areas': [line.strip() for line in request.form.get('interest_areas', '').split('\n') if line.strip()],
            'contact_details': json.loads(request.form.get('contact_details_json', '[]')),
            'resume': {
                'enabled': request.form.get('resume_enabled') == 'on',
                'heading': request.form.get('resume_heading', ''),
                'description': request.form.get('resume_description', ''),
                'button_text': request.form.get('resume_button_text', ''),
                'file_path': request.form.get('resume_file_path', 'portfolio/downloads/Samridhi_Chordia_Resume.pdf')
            },
            'form': {
                'enabled': True,
                'heading': request.form.get('form_heading', ''),
                'intro': request.form.get('form_intro', ''),
                'response_time': request.form.get('form_response_time', '')
            }
        }

        # Handle resume file upload if provided
        if 'resume_file' in request.files:
            file = request.files['resume_file']
            if file and file.filename and file.filename.endswith('.pdf'):
                filename = secure_filename(file.filename)
                upload_dir = os.path.join(current_app.static_folder, 'portfolio/downloads')
                os.makedirs(upload_dir, exist_ok=True)
                filepath = os.path.join(upload_dir, filename)
                file.save(filepath)
                data['resume']['file_path'] = f'portfolio/downloads/{filename}'

        # Determine action
        action = request.form.get('action', 'save_draft')
        as_draft = (action == 'save_draft')

        if save_page_data('contact', data, as_draft=as_draft):
            if as_draft:
                flash('Contact page saved as draft', 'success')
            else:
                flash('Contact page published successfully', 'success')
        else:
            flash('Error saving contact page', 'error')

        return redirect(url_for('admin_portfolio.edit_contact_page'))

    # Load existing data
    page_data, is_draft = load_page_data('contact')

    return render_template('admin/portfolio/page_contact_form.html',
                         page=page_data,
                         is_draft=is_draft)

@admin_portfolio_bp.route('/pages/<page_id>/publish', methods=['POST'])
@login_required
@admin_required
def publish_page(page_id):
    """Publish a draft page"""
    try:
        draft_path = get_page_path(page_id, is_draft=True)
        published_path = get_page_path(page_id, is_draft=False)

        if not os.path.exists(draft_path):
            flash('No draft found to publish', 'error')
            return redirect(url_for('admin_portfolio.list_pages'))

        shutil.copy2(draft_path, published_path)
        os.remove(draft_path)

        flash(f'{page_id.title()} page published successfully', 'success')
    except Exception as e:
        flash(f'Error publishing page: {str(e)}', 'error')

    return redirect(url_for('admin_portfolio.list_pages'))

@admin_portfolio_bp.route('/pages/<page_id>/revert', methods=['POST'])
@login_required
@admin_required
def revert_page(page_id):
    """Revert to published version (discard draft)"""
    try:
        draft_path = get_page_path(page_id, is_draft=True)

        if not os.path.exists(draft_path):
            flash('No draft found to revert', 'error')
            return redirect(url_for('admin_portfolio.list_pages'))

        os.remove(draft_path)
        flash(f'Draft discarded for {page_id} page', 'success')
    except Exception as e:
        flash(f'Error reverting page: {str(e)}', 'error')

    return redirect(url_for('admin_portfolio.list_pages'))

# ============================================================================
# FILE UPLOAD HANDLERS
# ============================================================================

@admin_portfolio_bp.route('/upload/image', methods=['POST'])
@login_required
@admin_required
def upload_image():
    """Handle image upload via AJAX"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        content_type = request.form.get('content_type', 'projects')
        content_id = request.form.get('content_id')

        if not content_id:
            return jsonify({'error': 'No content ID provided'}), 400

        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_image_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed: png, jpg, jpeg, gif, webp'}), 400

        # Check file size
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)

        if size > 10 * 1024 * 1024:  # 10MB
            return jsonify({'error': 'File too large (max 10MB)'}), 400

        # Save with timestamp prefix
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"

        upload_dir = get_upload_path(content_type, content_id, 'images')
        os.makedirs(upload_dir, exist_ok=True)

        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)

        # Return relative path for JSON storage
        relative_path = f"images/{content_type}/{content_id}/{filename}"

        return jsonify({
            'success': True,
            'path': relative_path,
            'url': f"/static/portfolio/{relative_path}"
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@admin_portfolio_bp.route('/upload/video', methods=['POST'])
@login_required
@admin_required
def upload_video():
    """Handle video upload via AJAX"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        content_type = request.form.get('content_type', 'projects')
        content_id = request.form.get('content_id')

        if not content_id:
            return jsonify({'error': 'No content ID provided'}), 400

        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_video_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed: mp4, webm, mov'}), 400

        # Check file size
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)

        if size > 50 * 1024 * 1024:  # 50MB
            return jsonify({'error': 'File too large (max 50MB)'}), 400

        # Save with timestamp prefix
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"

        upload_dir = get_upload_path(content_type, content_id, 'videos')
        os.makedirs(upload_dir, exist_ok=True)

        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)

        # Return relative path for JSON storage
        relative_path = f"videos/{content_type}/{content_id}/{filename}"

        return jsonify({
            'success': True,
            'path': relative_path,
            'url': f"/static/portfolio/{relative_path}"
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
