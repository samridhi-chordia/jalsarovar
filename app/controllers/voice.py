"""
Voice Agent Controller
Handles Twilio webhook endpoints for SMS, Voice, and WhatsApp
Also provides frontend UI routes for user-facing pages
"""
from flask import Blueprint, request, Response, current_app, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.services.notification_service import NotificationService
from app.services.water_status_service import WaterStatusService
from app.services.voice_response_service import VoiceResponseService
from app.models.notification_log import NotificationLog
from sqlalchemy import desc, func
from datetime import datetime, timedelta

voice_bp = Blueprint('voice', __name__, url_prefix='/api/voice')


# ============================================================================
# VOICE CALL ENDPOINTS
# ============================================================================

@voice_bp.route('/incoming-call', methods=['POST'])
def incoming_call():
    """
    Handle incoming voice call - welcome menu
    Webhook: Triggered when a call comes in
    """
    current_app.logger.info(f"Incoming call from: {request.form.get('From')}")

    twiml = VoiceResponseService.generate_welcome_menu()

    return Response(twiml, mimetype='application/xml')


@voice_bp.route('/menu-selection', methods=['POST'])
def handle_menu_selection():
    """
    Handle main menu DTMF selection
    Webhook: Triggered after user presses a digit
    """
    digit = request.form.get('Digits')
    current_app.logger.info(f"Menu selection: {digit}")

    if digit == '1':
        # Public water site information
        twiml = VoiceResponseService.generate_site_code_prompt(site_type='public')
    elif digit == '2':
        # Residential monitoring
        twiml = VoiceResponseService.generate_site_code_prompt(site_type='residential')
    elif digit == '9':
        # Repeat menu
        twiml = VoiceResponseService.generate_welcome_menu()
    else:
        # Invalid selection
        twiml = VoiceResponseService.generate_error_response(
            "Invalid selection. Please try again.",
            allow_retry=True
        )

    return Response(twiml, mimetype='application/xml')


@voice_bp.route('/process-public-site', methods=['POST'])
def process_public_site():
    """
    Process public site query from speech recognition
    Webhook: Triggered after speech input
    """
    speech_result = request.form.get('SpeechResult')
    current_app.logger.info(f"Public site speech input: {speech_result}")

    if not speech_result:
        twiml = VoiceResponseService.generate_error_response(
            "I didn't catch that. Please try again.",
            allow_retry=True
        )
        return Response(twiml, mimetype='application/xml')

    # Parse speech input
    site_query = VoiceResponseService.parse_speech_input(speech_result)

    # Get site status
    status_data = WaterStatusService.get_public_site_status(site_query)

    if status_data:
        twiml = VoiceResponseService.generate_status_response(status_data, site_type='public')
    else:
        twiml = VoiceResponseService.generate_site_not_found(site_query, site_type='public')

    return Response(twiml, mimetype='application/xml')


@voice_bp.route('/process-residential-site', methods=['POST'])
def process_residential_site():
    """
    Process residential site query from speech recognition
    Webhook: Triggered after speech input
    """
    speech_result = request.form.get('SpeechResult')
    current_app.logger.info(f"Residential site speech input: {speech_result}")

    if not speech_result:
        twiml = VoiceResponseService.generate_error_response(
            "I didn't catch that. Please try again.",
            allow_retry=True
        )
        return Response(twiml, mimetype='application/xml')

    # Parse speech input
    site_query = VoiceResponseService.parse_speech_input(speech_result)

    # Get site status
    status_data = WaterStatusService.get_residential_site_status(site_query)

    if status_data:
        twiml = VoiceResponseService.generate_status_response(status_data, site_type='residential')
    else:
        twiml = VoiceResponseService.generate_site_not_found(site_query, site_type='residential')

    return Response(twiml, mimetype='application/xml')


@voice_bp.route('/repeat-menu', methods=['POST'])
def handle_repeat_menu():
    """
    Handle repeat or return to menu selection
    Webhook: Triggered from status response menu
    """
    digit = request.form.get('Digits')
    site_type = request.args.get('site_type', 'public')

    if digit == '1':
        # Repeat last status (redirect back to site prompt)
        twiml = VoiceResponseService.generate_site_code_prompt(site_type=site_type)
    elif digit == '2':
        # Return to main menu
        twiml = VoiceResponseService.generate_welcome_menu()
    elif digit == '9':
        # End call
        twiml = VoiceResponseService.generate_goodbye()
    else:
        # Default to goodbye
        twiml = VoiceResponseService.generate_goodbye()

    return Response(twiml, mimetype='application/xml')


@voice_bp.route('/error-retry', methods=['POST'])
def handle_error_retry():
    """
    Handle error retry selection
    """
    digit = request.form.get('Digits')

    if digit == '1':
        # Try again - return to welcome
        twiml = VoiceResponseService.generate_welcome_menu()
    else:
        # Return to main menu
        twiml = VoiceResponseService.generate_welcome_menu()

    return Response(twiml, mimetype='application/xml')


@voice_bp.route('/site-retry', methods=['POST'])
def handle_site_retry():
    """
    Handle site not found retry selection
    """
    digit = request.form.get('Digits')
    site_type = request.args.get('site_type', 'public')

    if digit == '1':
        # Try different site
        twiml = VoiceResponseService.generate_site_code_prompt(site_type=site_type)
    else:
        # Return to main menu
        twiml = VoiceResponseService.generate_welcome_menu()

    return Response(twiml, mimetype='application/xml')


@voice_bp.route('/welcome', methods=['POST', 'GET'])
def welcome():
    """
    Welcome endpoint - can be called directly
    """
    twiml = VoiceResponseService.generate_welcome_menu()
    return Response(twiml, mimetype='application/xml')


@voice_bp.route('/help', methods=['POST'])
def help_message():
    """
    Help message endpoint
    """
    twiml = VoiceResponseService.generate_help_message()
    return Response(twiml, mimetype='application/xml')


# ============================================================================
# SMS ENDPOINTS
# ============================================================================

@voice_bp.route('/sms/incoming', methods=['POST'])
def incoming_sms():
    """
    Handle incoming SMS message
    Webhook: Triggered when SMS is received
    """
    from_number = request.form.get('From')
    message_body = request.form.get('Body', '').strip()

    current_app.logger.info(f"Incoming SMS from {from_number}: {message_body}")

    # Parse message to extract site code
    site_query = message_body.upper()

    # Try public site first
    status_data = WaterStatusService.get_public_site_status(site_query)

    if not status_data:
        # Try residential site
        status_data = WaterStatusService.get_residential_site_status(site_query)

    # Format response
    if status_data:
        response_text = WaterStatusService.format_sms_response(status_data)
    else:
        response_text = (
            f"Site '{message_body}' not found. "
            "Please send a valid site code or name. "
            "Example: 'ABC123' or 'DEVICE456'"
        )

    # Send SMS response using Twilio MessagingResponse
    try:
        from twilio.twiml.messaging_response import MessagingResponse

        resp = MessagingResponse()
        resp.message(response_text)

        return Response(str(resp), mimetype='application/xml')

    except ImportError:
        current_app.logger.error("Twilio library not installed")
        return Response("Error processing request", status=500)


@voice_bp.route('/sms/status', methods=['POST'])
def sms_status_callback():
    """
    Handle SMS status callback from Twilio
    Webhook: Triggered when SMS status changes
    """
    message_sid = request.form.get('MessageSid')
    message_status = request.form.get('MessageStatus')
    error_code = request.form.get('ErrorCode')
    error_message = request.form.get('ErrorMessage')

    current_app.logger.info(f"SMS status update: {message_sid} - {message_status}")

    # Update notification log
    notification_service = NotificationService()
    notification_service.update_status_from_webhook(
        message_sid,
        message_status,
        error_code,
        error_message
    )

    return Response('OK', status=200)


# ============================================================================
# WHATSAPP ENDPOINTS
# ============================================================================

@voice_bp.route('/whatsapp/incoming', methods=['POST'])
def incoming_whatsapp():
    """
    Handle incoming WhatsApp message
    Webhook: Triggered when WhatsApp message is received
    """
    from_number = request.form.get('From')
    message_body = request.form.get('Body', '').strip()

    current_app.logger.info(f"Incoming WhatsApp from {from_number}: {message_body}")

    # Parse message to extract site code
    site_query = message_body.upper()

    # Try public site first
    status_data = WaterStatusService.get_public_site_status(site_query)

    if not status_data:
        # Try residential site
        status_data = WaterStatusService.get_residential_site_status(site_query)

    # Format response for WhatsApp (supports rich formatting)
    if status_data:
        response_text = WaterStatusService.format_whatsapp_response(status_data)
    else:
        response_text = (
            "🔍 *Site Not Found*\n\n"
            f"I couldn't find a site matching '{message_body}'.\n\n"
            "Please send a valid:\n"
            "• Site code (e.g., ABC123)\n"
            "• Site name (e.g., Ganges River)\n"
            "• Device ID (e.g., DEVICE456)\n\n"
            "Need help? Reply with 'HELP'"
        )

    # Send WhatsApp response
    try:
        from twilio.twiml.messaging_response import MessagingResponse

        resp = MessagingResponse()
        resp.message(response_text)

        return Response(str(resp), mimetype='application/xml')

    except ImportError:
        current_app.logger.error("Twilio library not installed")
        return Response("Error processing request", status=500)


@voice_bp.route('/whatsapp/status', methods=['POST'])
def whatsapp_status_callback():
    """
    Handle WhatsApp status callback from Twilio
    Webhook: Triggered when WhatsApp message status changes
    """
    message_sid = request.form.get('MessageSid')
    message_status = request.form.get('MessageStatus')
    error_code = request.form.get('ErrorCode')
    error_message = request.form.get('ErrorMessage')

    current_app.logger.info(f"WhatsApp status update: {message_sid} - {message_status}")

    # Update notification log
    notification_service = NotificationService()
    notification_service.update_status_from_webhook(
        message_sid,
        message_status,
        error_code,
        error_message
    )

    return Response('OK', status=200)


# ============================================================================
# CALL STATUS ENDPOINT
# ============================================================================

@voice_bp.route('/call/status', methods=['POST'])
def call_status_callback():
    """
    Handle call status callback from Twilio
    Webhook: Triggered when call status changes
    """
    call_sid = request.form.get('CallSid')
    call_status = request.form.get('CallStatus')
    call_duration = request.form.get('CallDuration')

    current_app.logger.info(
        f"Call status update: {call_sid} - {call_status} "
        f"(Duration: {call_duration}s)"
    )

    # Update notification log
    notification_service = NotificationService()
    notification_service.update_status_from_webhook(
        call_sid,
        call_status
    )

    return Response('OK', status=200)


# ============================================================================
# HEALTH CHECK & UTILITY ENDPOINTS
# ============================================================================

@voice_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring
    """
    return {
        'status': 'healthy',
        'service': 'Jal Sarovar Voice Agent',
        'version': '1.0.0'
    }, 200


@voice_bp.route('/test', methods=['GET'])
def test_endpoint():
    """
    Test endpoint to verify TwiML generation
    """
    twiml = VoiceResponseService.generate_welcome_menu()
    return Response(twiml, mimetype='application/xml')


# ============================================================================
# FRONTEND UI ROUTES
# ============================================================================

@voice_bp.route('/info', methods=['GET'])
def info_page():
    """
    Voice Agent information page - how to use voice, SMS, WhatsApp
    Public access (no login required)
    """
    phone_number = current_app.config.get('TWILIO_PHONE_NUMBER', 'Not configured')
    whatsapp_number = current_app.config.get('TWILIO_WHATSAPP_NUMBER', 'Not configured')

    voice_enabled = current_app.config.get('VOICE_ENABLED', False)
    sms_enabled = current_app.config.get('SMS_ENABLED', False)
    whatsapp_enabled = current_app.config.get('WHATSAPP_ENABLED', False)

    return render_template('voice/info.html',
                         phone_number=phone_number,
                         whatsapp_number=whatsapp_number,
                         voice_enabled=voice_enabled,
                         sms_enabled=sms_enabled,
                         whatsapp_enabled=whatsapp_enabled)


@voice_bp.route('/my-notifications', methods=['GET'])
@login_required
def my_notifications():
    """
    User's notification history (SMS, voice, WhatsApp sent to them)
    Requires login
    """
    # Get user's notifications (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    notifications = NotificationLog.query.filter(
        NotificationLog.created_at >= thirty_days_ago
    ).order_by(desc(NotificationLog.created_at)).limit(100).all()

    # Get statistics
    stats = NotificationLog.get_statistics(days=30)

    return render_template('voice/my_notifications.html',
                         notifications=notifications,
                         stats=stats)


@voice_bp.route('/admin/dashboard', methods=['GET'])
@login_required
def admin_dashboard():
    """
    Admin dashboard for monitoring voice agent system
    Shows Twilio usage, costs, statistics
    Requires admin login
    """
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))

    # Get statistics for different time periods
    stats_7d = NotificationLog.get_statistics(days=7)
    stats_30d = NotificationLog.get_statistics(days=30)

    # Get recent notifications (last 50)
    recent_notifications = NotificationLog.query.order_by(
        desc(NotificationLog.created_at)
    ).limit(50).all()

    # Get failed notifications for troubleshooting
    failed_notifications = NotificationLog.query.filter_by(
        status='failed'
    ).order_by(desc(NotificationLog.created_at)).limit(20).all()

    # Get notification counts by type
    notification_counts = db.session.query(
        NotificationLog.notification_type,
        func.count(NotificationLog.id).label('count')
    ).group_by(NotificationLog.notification_type).all()

    # Get notification counts by status
    status_counts = db.session.query(
        NotificationLog.status,
        func.count(NotificationLog.id).label('count')
    ).group_by(NotificationLog.status).all()

    # Configuration info
    account_sid = current_app.config.get('TWILIO_ACCOUNT_SID', 'Not configured')
    twilio_config = {
        'account_sid': (account_sid[:20] + '...') if account_sid and account_sid != 'Not configured' else account_sid,
        'phone_number': current_app.config.get('TWILIO_PHONE_NUMBER', 'Not configured'),
        'whatsapp_number': current_app.config.get('TWILIO_WHATSAPP_NUMBER', 'Not configured'),
        'voice_enabled': current_app.config.get('VOICE_ENABLED', False),
        'sms_enabled': current_app.config.get('SMS_ENABLED', False),
        'whatsapp_enabled': current_app.config.get('WHATSAPP_ENABLED', False),
    }

    return render_template('voice/admin_dashboard.html',
                         stats_7d=stats_7d,
                         stats_30d=stats_30d,
                         recent_notifications=recent_notifications,
                         failed_notifications=failed_notifications,
                         notification_counts=dict(notification_counts),
                         status_counts=dict(status_counts),
                         twilio_config=twilio_config)


@voice_bp.route('/admin/retry/<int:log_id>', methods=['POST'])
@login_required
def retry_notification(log_id):
    """
    Retry a failed notification
    Admin only
    """
    if not current_user.is_admin():
        flash('Access denied. Admin privileges required.', 'error')
        return redirect(url_for('main.dashboard'))

    notification_service = NotificationService()
    success = notification_service.retry_failed_notification(log_id)

    if success:
        flash('Notification retry successful.', 'success')
    else:
        flash('Failed to retry notification. Check logs for details.', 'error')

    return redirect(url_for('voice.admin_dashboard'))
