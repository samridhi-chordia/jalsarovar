"""Settings controller for system configuration management"""
from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import SystemConfig, CONFIGURABLE_SETTINGS, CONFIG_CATEGORIES

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')


@settings_bp.route('/')
@login_required
def index():
    """Settings page"""
    return render_template('settings/index.html')


@settings_bp.route('/api/config', methods=['GET'])
@login_required
def get_all_config():
    """Get all configuration settings with their current values"""
    # Get all settings organized by category
    settings_by_category = {}

    for key, metadata in CONFIGURABLE_SETTINGS.items():
        category = metadata['category']
        if category not in settings_by_category:
            settings_by_category[category] = {
                'settings': [],
                **CONFIG_CATEGORIES.get(category, {'label': category.title(), 'icon': 'gear', 'order': 99})
            }

        # Check for user override in database
        db_config = SystemConfig.query.filter_by(key=key).first()
        if db_config:
            current_value = db_config.get_value()
            is_default = False
            updated_at = db_config.updated_at.isoformat() if db_config.updated_at else None
            updated_by = db_config.updated_by.username if db_config.updated_by else None
        else:
            current_value = metadata['value']
            is_default = True
            updated_at = None
            updated_by = None

        settings_by_category[category]['settings'].append({
            'key': key,
            'value': current_value,
            'default_value': metadata['value'],
            'value_type': metadata['value_type'],
            'description': metadata['description'],
            'is_default': is_default,
            'updated_at': updated_at,
            'updated_by': updated_by,
            **{k: v for k, v in metadata.items() if k in ['options', 'min', 'max']}
        })

    # Sort categories by order
    sorted_categories = dict(sorted(
        settings_by_category.items(),
        key=lambda x: x[1].get('order', 99)
    ))

    return jsonify({
        'success': True,
        'categories': sorted_categories
    })


@settings_bp.route('/api/config/<key>', methods=['GET'])
@login_required
def get_config(key):
    """Get a specific config value"""
    if key not in CONFIGURABLE_SETTINGS:
        return jsonify({'success': False, 'error': f'Unknown config key: {key}'}), 400

    metadata = CONFIGURABLE_SETTINGS[key]
    db_config = SystemConfig.query.filter_by(key=key).first()

    if db_config:
        value = db_config.get_value()
        is_default = False
    else:
        value = metadata['value']
        is_default = True

    return jsonify({
        'success': True,
        'key': key,
        'value': value,
        'default_value': metadata['value'],
        'is_default': is_default,
        'metadata': metadata
    })


@settings_bp.route('/api/config/<key>', methods=['PUT'])
@login_required
def update_config(key):
    """Update a specific config value"""
    if key not in CONFIGURABLE_SETTINGS:
        return jsonify({'success': False, 'error': f'Unknown config key: {key}'}), 400

    # Check admin permission
    if not current_user.is_admin():
        return jsonify({'success': False, 'error': 'Admin permission required'}), 403

    data = request.get_json()
    if 'value' not in data:
        return jsonify({'success': False, 'error': 'Value is required'}), 400

    metadata = CONFIGURABLE_SETTINGS[key]
    value = data['value']

    # Validate value type
    try:
        if metadata['value_type'] == 'int':
            value = int(value)
            # Validate min/max
            if 'min' in metadata and value < metadata['min']:
                return jsonify({'success': False, 'error': f'Value must be at least {metadata["min"]}'}), 400
            if 'max' in metadata and value > metadata['max']:
                return jsonify({'success': False, 'error': f'Value must be at most {metadata["max"]}'}), 400
        elif metadata['value_type'] == 'float':
            value = float(value)
            if 'min' in metadata and value < metadata['min']:
                return jsonify({'success': False, 'error': f'Value must be at least {metadata["min"]}'}), 400
            if 'max' in metadata and value > metadata['max']:
                return jsonify({'success': False, 'error': f'Value must be at most {metadata["max"]}'}), 400
        elif metadata['value_type'] == 'bool':
            value = bool(value)
        elif 'options' in metadata and value not in metadata['options']:
            return jsonify({'success': False, 'error': f'Value must be one of: {metadata["options"]}'}), 400
    except (ValueError, TypeError) as e:
        return jsonify({'success': False, 'error': f'Invalid value type: {str(e)}'}), 400

    # Save to database
    config = SystemConfig.set(
        key=key,
        value=value,
        value_type=metadata['value_type'],
        category=metadata['category'],
        description=metadata['description'],
        user_id=current_user.id
    )

    return jsonify({
        'success': True,
        'key': key,
        'value': config.get_value(),
        'message': f'Setting {key} updated successfully'
    })


@settings_bp.route('/api/config/<key>', methods=['DELETE'])
@login_required
def reset_config(key):
    """Reset a config value to default (delete override)"""
    if key not in CONFIGURABLE_SETTINGS:
        return jsonify({'success': False, 'error': f'Unknown config key: {key}'}), 400

    # Check admin permission
    if not current_user.is_admin():
        return jsonify({'success': False, 'error': 'Admin permission required'}), 403

    db_config = SystemConfig.query.filter_by(key=key).first()
    if db_config:
        db.session.delete(db_config)
        db.session.commit()

    return jsonify({
        'success': True,
        'key': key,
        'value': CONFIGURABLE_SETTINGS[key]['value'],
        'message': f'Setting {key} reset to default'
    })


@settings_bp.route('/api/config/reset-all', methods=['POST'])
@login_required
def reset_all_config():
    """Reset all config values to defaults"""
    # Check admin permission
    if not current_user.is_admin():
        return jsonify({'success': False, 'error': 'Admin permission required'}), 403

    count = SystemConfig.query.delete()
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Reset {count} settings to defaults'
    })


@settings_bp.route('/api/config/export', methods=['GET'])
@login_required
def export_config():
    """Export all current config values as JSON"""
    config_data = {}
    for key, metadata in CONFIGURABLE_SETTINGS.items():
        db_config = SystemConfig.query.filter_by(key=key).first()
        config_data[key] = db_config.get_value() if db_config else metadata['value']

    return jsonify({
        'success': True,
        'config': config_data
    })


@settings_bp.route('/api/config/import', methods=['POST'])
@login_required
def import_config():
    """Import config values from JSON"""
    if not current_user.is_admin():
        return jsonify({'success': False, 'error': 'Admin permission required'}), 403

    data = request.get_json()
    if 'config' not in data:
        return jsonify({'success': False, 'error': 'Config data required'}), 400

    imported = 0
    errors = []

    for key, value in data['config'].items():
        if key not in CONFIGURABLE_SETTINGS:
            errors.append(f'Unknown key: {key}')
            continue

        metadata = CONFIGURABLE_SETTINGS[key]
        try:
            SystemConfig.set(
                key=key,
                value=value,
                value_type=metadata['value_type'],
                category=metadata['category'],
                description=metadata['description'],
                user_id=current_user.id
            )
            imported += 1
        except Exception as e:
            errors.append(f'{key}: {str(e)}')

    return jsonify({
        'success': True,
        'imported': imported,
        'errors': errors
    })
