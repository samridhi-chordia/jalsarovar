"""
Notification Service
Handles SMS, Voice, and WhatsApp notifications via Twilio for the voice agent system.
"""
import time
from datetime import datetime
from flask import current_app
import phonenumbers
from phonenumbers import NumberParseException

from app import db
from app.models.notification_log import NotificationLog


class NotificationService:
    """Service for sending notifications via Twilio (SMS, Voice, WhatsApp)"""

    def __init__(self):
        """Initialize Twilio client if credentials are configured"""
        self.account_sid = current_app.config.get('TWILIO_ACCOUNT_SID')
        self.auth_token = current_app.config.get('TWILIO_AUTH_TOKEN')
        self.phone_number = current_app.config.get('TWILIO_PHONE_NUMBER')
        self.whatsapp_number = current_app.config.get('TWILIO_WHATSAPP_NUMBER')
        self.client = None

        # Initialize Twilio client
        if self.account_sid and self.auth_token:
            try:
                from twilio.rest import Client
                self.client = Client(self.account_sid, self.auth_token)
                current_app.logger.info("Twilio client initialized successfully")
            except ImportError:
                current_app.logger.error("Twilio library not installed. Run: pip install twilio")
            except Exception as e:
                current_app.logger.error(f"Failed to initialize Twilio client: {e}")
        else:
            current_app.logger.warning("Twilio credentials not configured")

    def validate_phone_number(self, phone_number, default_region="IN"):
        """
        Validate and format phone number to E.164 format

        Args:
            phone_number: Phone number string
            default_region: Default country code (default: India)

        Returns:
            Formatted phone number in E.164 format or None if invalid
        """
        try:
            parsed = phonenumbers.parse(phone_number, default_region)
            if not phonenumbers.is_valid_number(parsed):
                current_app.logger.warning(f"Invalid phone number: {phone_number}")
                return None
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        except NumberParseException as e:
            current_app.logger.error(f"Phone number parse error for {phone_number}: {e}")
            return None

    def send_sms(self, to_phone, message, site_identifier=None, site_type=None):
        """
        Send SMS via Twilio

        Args:
            to_phone: Recipient phone number
            message: SMS message content
            site_identifier: Optional site code or device ID
            site_type: Optional 'public' or 'residential'

        Returns:
            Twilio message SID if successful, None otherwise
        """
        if not current_app.config.get('SMS_ENABLED'):
            current_app.logger.info(f"SMS disabled. Would send to {to_phone}: {message}")
            return None

        if not self.client:
            current_app.logger.error("Twilio client not initialized")
            return None

        # Validate phone number
        to_phone = self.validate_phone_number(to_phone)
        if not to_phone:
            current_app.logger.error(f"Invalid phone number for SMS")
            return None

        # Create log entry
        log = NotificationLog(
            notification_type='sms',
            site_type=site_type,
            site_identifier=site_identifier,
            recipient_phone=to_phone,
            message_content=message,
            status='pending'
        )
        db.session.add(log)
        db.session.commit()

        # Send SMS
        try:
            from twilio.base.exceptions import TwilioRestException

            twilio_message = self.client.messages.create(
                body=message,
                from_=self.phone_number,
                to=to_phone
            )

            # Update log
            log.twilio_message_sid = twilio_message.sid
            log.status = twilio_message.status
            log.sent_at = datetime.utcnow()
            db.session.commit()

            current_app.logger.info(f"SMS sent: {twilio_message.sid} to {to_phone}")
            return twilio_message.sid

        except TwilioRestException as e:
            log.status = 'failed'
            log.error_message = str(e)
            log.twilio_error_code = str(e.code) if hasattr(e, 'code') else None
            log.failed_at = datetime.utcnow()
            db.session.commit()
            current_app.logger.error(f"SMS failed: {e}")
            return None
        except Exception as e:
            log.status = 'failed'
            log.error_message = str(e)
            log.failed_at = datetime.utcnow()
            db.session.commit()
            current_app.logger.error(f"Unexpected error sending SMS: {e}")
            return None

    def send_whatsapp(self, to_phone, message, site_identifier=None, site_type=None):
        """
        Send WhatsApp message via Twilio

        Args:
            to_phone: Recipient phone number
            message: WhatsApp message content
            site_identifier: Optional site code or device ID
            site_type: Optional 'public' or 'residential'

        Returns:
            Twilio message SID if successful, None otherwise
        """
        if not current_app.config.get('WHATSAPP_ENABLED'):
            current_app.logger.info(f"WhatsApp disabled. Would send to {to_phone}: {message}")
            return None

        if not self.client:
            current_app.logger.error("Twilio client not initialized")
            return None

        # Validate and format phone number
        validated_phone = self.validate_phone_number(to_phone)
        if not validated_phone:
            return None

        # WhatsApp requires whatsapp: prefix
        if not validated_phone.startswith('whatsapp:'):
            to_phone_formatted = f'whatsapp:{validated_phone}'
        else:
            to_phone_formatted = validated_phone

        # Create log entry
        log = NotificationLog(
            notification_type='whatsapp',
            site_type=site_type,
            site_identifier=site_identifier,
            recipient_phone=to_phone_formatted,
            message_content=message,
            status='pending'
        )
        db.session.add(log)
        db.session.commit()

        try:
            from twilio.base.exceptions import TwilioRestException

            twilio_message = self.client.messages.create(
                body=message,
                from_=self.whatsapp_number,
                to=to_phone_formatted
            )

            # Update log
            log.twilio_message_sid = twilio_message.sid
            log.status = twilio_message.status
            log.sent_at = datetime.utcnow()
            db.session.commit()

            current_app.logger.info(f"WhatsApp sent: {twilio_message.sid} to {to_phone_formatted}")
            return twilio_message.sid

        except TwilioRestException as e:
            log.status = 'failed'
            log.error_message = str(e)
            log.twilio_error_code = str(e.code) if hasattr(e, 'code') else None
            log.failed_at = datetime.utcnow()
            db.session.commit()
            current_app.logger.error(f"WhatsApp failed: {e}")
            return None
        except Exception as e:
            log.status = 'failed'
            log.error_message = str(e)
            log.failed_at = datetime.utcnow()
            db.session.commit()
            current_app.logger.error(f"Unexpected error sending WhatsApp: {e}")
            return None

    def make_voice_call(self, to_phone, twiml_url, site_identifier=None, site_type=None):
        """
        Initiate voice call with TwiML URL

        Args:
            to_phone: Recipient phone number
            twiml_url: URL that returns TwiML instructions
            site_identifier: Optional site code or device ID
            site_type: Optional 'public' or 'residential'

        Returns:
            Twilio call SID if successful, None otherwise
        """
        if not current_app.config.get('VOICE_ENABLED'):
            current_app.logger.info(f"Voice disabled. Would call {to_phone} with TwiML: {twiml_url}")
            return None

        if not self.client:
            current_app.logger.error("Twilio client not initialized")
            return None

        # Validate phone number
        to_phone = self.validate_phone_number(to_phone)
        if not to_phone:
            return None

        # Create log entry
        log = NotificationLog(
            notification_type='voice',
            site_type=site_type,
            site_identifier=site_identifier,
            recipient_phone=to_phone,
            message_content=f'Voice call to: {twiml_url}',
            status='pending'
        )
        db.session.add(log)
        db.session.commit()

        try:
            from twilio.base.exceptions import TwilioRestException

            call = self.client.calls.create(
                url=twiml_url,
                to=to_phone,
                from_=self.phone_number
            )

            # Update log
            log.twilio_message_sid = call.sid
            log.status = call.status
            log.sent_at = datetime.utcnow()
            db.session.commit()

            current_app.logger.info(f"Voice call initiated: {call.sid} to {to_phone}")
            return call.sid

        except TwilioRestException as e:
            log.status = 'failed'
            log.error_message = str(e)
            log.twilio_error_code = str(e.code) if hasattr(e, 'code') else None
            log.failed_at = datetime.utcnow()
            db.session.commit()
            current_app.logger.error(f"Voice call failed: {e}")
            return None
        except Exception as e:
            log.status = 'failed'
            log.error_message = str(e)
            log.failed_at = datetime.utcnow()
            db.session.commit()
            current_app.logger.error(f"Unexpected error making voice call: {e}")
            return None

    def retry_failed_notification(self, log_id):
        """
        Retry a failed notification

        Args:
            log_id: NotificationLog ID to retry

        Returns:
            True if retry successful, False otherwise
        """
        log = NotificationLog.query.get(log_id)
        if not log:
            current_app.logger.error(f"Notification log {log_id} not found")
            return False

        if log.status != 'failed':
            current_app.logger.warning(f"Notification log {log_id} is not in failed status")
            return False

        max_retries = current_app.config.get('NOTIFICATION_RETRY_ATTEMPTS', 3)
        if log.retry_count >= max_retries:
            current_app.logger.warning(f"Max retries ({max_retries}) exceeded for log {log_id}")
            return False

        # Update retry tracking
        log.retry_count += 1
        log.last_retry_at = datetime.utcnow()
        db.session.commit()

        # Retry based on notification type
        if log.notification_type == 'sms':
            return self.send_sms(
                log.recipient_phone,
                log.message_content,
                log.site_identifier,
                log.site_type
            ) is not None
        elif log.notification_type == 'whatsapp':
            return self.send_whatsapp(
                log.recipient_phone,
                log.message_content,
                log.site_identifier,
                log.site_type
            ) is not None
        elif log.notification_type == 'voice':
            # Extract TwiML URL from message_content
            twiml_url = log.message_content.replace('Voice call to: ', '')
            return self.make_voice_call(
                log.recipient_phone,
                twiml_url,
                log.site_identifier,
                log.site_type
            ) is not None
        else:
            current_app.logger.error(f"Unknown notification type: {log.notification_type}")
            return False

    def update_status_from_webhook(self, message_sid, status, error_code=None, error_message=None):
        """
        Update notification status from Twilio webhook callback

        Args:
            message_sid: Twilio message/call SID
            status: New status from Twilio
            error_code: Optional error code
            error_message: Optional error message
        """
        log = NotificationLog.query.filter_by(twilio_message_sid=message_sid).first()
        if not log:
            current_app.logger.warning(f"Notification log not found for SID: {message_sid}")
            return

        log.status = status

        if status == 'delivered':
            log.delivered_at = datetime.utcnow()
        elif status in ['failed', 'undelivered']:
            log.failed_at = datetime.utcnow()
            if error_code:
                log.twilio_error_code = error_code
            if error_message:
                log.error_message = error_message

        db.session.commit()
        current_app.logger.info(f"Updated notification {message_sid} status to {status}")
