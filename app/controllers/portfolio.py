"""
Portfolio Blueprint - Samridhi Chordia Personal Portfolio
Integrated into Jal Sarovar application at /samridhi-chordia/
"""
from flask import Blueprint, render_template, jsonify, request, current_app
import json
import os

portfolio_bp = Blueprint('portfolio', __name__, template_folder='../templates/portfolio')


def load_content_item(item_type, item_id):
    """
    Load a content item (project, volunteer, interest) by ID

    Args:
        item_type: 'project', 'volunteer', or 'interest'
        item_id: The item's unique identifier

    Returns:
        dict: Content item data or None if not found
    """
    type_map = {
        'project': 'projects',
        'volunteer': 'volunteer',
        'interest': 'interests'
    }

    folder = type_map.get(item_type)
    if not folder:
        return None

    item_path = os.path.join(current_app.static_folder,
                             f'portfolio/content/{folder}/{item_id}.json')
    try:
        with open(item_path) as f:
            data = json.load(f)
            data['content_type'] = item_type  # Add type for template logic
            return data
    except (IOError, json.JSONDecodeError, FileNotFoundError):
        return None


def load_page_content(page_id, is_draft=False):
    """
    Load page content from JSON file with fallback to None

    Args:
        page_id: The page identifier ('home', 'bio', 'contact')
        is_draft: Whether to load draft version (for admin preview)

    Returns:
        dict: Page content or None if file doesn't exist
    """
    content_dir = os.path.join(current_app.static_folder, 'portfolio/content/pages')

    # Try loading draft if requested
    if is_draft:
        draft_path = os.path.join(content_dir, f'{page_id}.draft.json')
        if os.path.exists(draft_path):
            try:
                with open(draft_path) as f:
                    content = json.load(f)
                    # Load featured items if this is the home page
                    if page_id == 'home' and 'featured_items' in content:
                        content['featured_content'] = []
                        for item in sorted(content.get('featured_items', []), key=lambda x: x.get('order', 0)):
                            loaded_item = load_content_item(item.get('type'), item.get('id'))
                            if loaded_item:
                                loaded_item['display_order'] = item.get('order', 0)
                                content['featured_content'].append(loaded_item)
                    return content
            except (IOError, json.JSONDecodeError):
                pass

    # Load published version
    published_path = os.path.join(content_dir, f'{page_id}.json')
    if os.path.exists(published_path):
        try:
            with open(published_path) as f:
                content = json.load(f)
                # Load featured items if this is the home page
                if page_id == 'home' and 'featured_items' in content:
                    content['featured_content'] = []
                    for item in sorted(content.get('featured_items', []), key=lambda x: x.get('order', 0)):
                        loaded_item = load_content_item(item.get('type'), item.get('id'))
                        if loaded_item:
                            loaded_item['display_order'] = item.get('order', 0)
                            content['featured_content'].append(loaded_item)
                return content
        except (IOError, json.JSONDecodeError):
            pass

    # Return None if no JSON exists (templates will use hardcoded fallbacks)
    return None


@portfolio_bp.route('/')
def home():
    """Portfolio home page"""
    page_content = load_page_content('home')
    return render_template('portfolio/index.html', active_page='home', page=page_content)


@portfolio_bp.route('/bio')
def bio():
    """About Samridhi page"""
    page_content = load_page_content('bio')
    return render_template('portfolio/about.html', active_page='about', page=page_content)


@portfolio_bp.route('/projects')
def projects():
    """Projects showcase"""
    return render_template('portfolio/projects.html', active_page='projects')


@portfolio_bp.route('/projects/<project_id>')
def project_detail(project_id):
    """Individual project detail page"""
    # Load project data from JSON
    json_path = os.path.join(current_app.static_folder,
                             f'portfolio/content/projects/{project_id}.json')
    try:
        with open(json_path) as f:
            project_data = json.load(f)
        return render_template('portfolio/project_detail.html',
                             project=project_data,
                             active_page='projects')
    except FileNotFoundError:
        return render_template('errors/404.html'), 404


@portfolio_bp.route('/volunteer')
def volunteer():
    """Volunteer work page"""
    # Load volunteer work from JSON files
    volunteer_dir = os.path.join(current_app.static_folder,
                                  'portfolio/content/volunteer')
    volunteer_list = []

    if os.path.exists(volunteer_dir):
        for filename in os.listdir(volunteer_dir):
            if filename.endswith('.json') and not filename.endswith('.draft.json'):
                try:
                    with open(os.path.join(volunteer_dir, filename)) as f:
                        volunteer_list.append(json.load(f))
                except (json.JSONDecodeError, IOError):
                    continue

    return render_template('portfolio/volunteer.html',
                         volunteer=volunteer_list,
                         active_page='volunteer')


@portfolio_bp.route('/interests')
def interests():
    """Personal interests page"""
    # Load interests from JSON files
    interests_dir = os.path.join(current_app.static_folder,
                                  'portfolio/content/interests')
    interests_list = []

    if os.path.exists(interests_dir):
        for filename in os.listdir(interests_dir):
            if filename.endswith('.json') and not filename.endswith('.draft.json'):
                try:
                    with open(os.path.join(interests_dir, filename)) as f:
                        interests_list.append(json.load(f))
                except (json.JSONDecodeError, IOError):
                    continue

    return render_template('portfolio/interests.html',
                         interests=interests_list,
                         active_page='interests')


@portfolio_bp.route('/blog')
def blog():
    """Blog listing page"""
    # Load articles from JSON
    json_path = os.path.join(current_app.static_folder,
                             'portfolio/content/blog/articles.json')
    try:
        with open(json_path) as f:
            articles_data = json.load(f)
        return render_template('portfolio/blog.html',
                             articles=articles_data.get('articles', []),
                             active_page='blog')
    except FileNotFoundError:
        articles_data = {'articles': []}
        return render_template('portfolio/blog.html',
                             articles=[],
                             active_page='blog')


@portfolio_bp.route('/blog/<slug>')
def blog_post(slug):
    """Individual blog post"""
    html_path = os.path.join(current_app.static_folder,
                            f'portfolio/content/blog/posts/{slug}.html')
    try:
        with open(html_path) as f:
            post_content = f.read()
        return render_template('portfolio/blog_post.html',
                             content=post_content,
                             active_page='blog')
    except FileNotFoundError:
        return render_template('errors/404.html'), 404


@portfolio_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    """Contact form page"""
    if request.method == 'POST':
        # Handle contact form submission
        # For now, just return success message (matching original behavior)
        return jsonify({'success': True, 'message': 'Thank you for your message!'})

    page_content = load_page_content('contact')
    return render_template('portfolio/contact.html', active_page='contact', page=page_content)


# API endpoints for dynamic content loading
@portfolio_bp.route('/api/projects')
def api_projects():
    """Return all projects as JSON"""
    projects_dir = os.path.join(current_app.static_folder,
                                'portfolio/content/projects')
    projects = []

    if os.path.exists(projects_dir):
        for filename in os.listdir(projects_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(projects_dir, filename)) as f:
                        projects.append(json.load(f))
                except (json.JSONDecodeError, IOError):
                    continue

    return jsonify(projects)
