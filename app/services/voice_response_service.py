"""
Voice Response Service
Generates TwiML (Twilio Markup Language) for IVR voice menus and responses.
"""
from flask import current_app, url_for


class VoiceResponseService:
    """Service for generating TwiML voice responses"""

    @staticmethod
    def generate_welcome_menu():
        """
        Generate welcome menu TwiML

        Returns:
            TwiML XML string
        """
        try:
            from twilio.twiml.voice_response import VoiceResponse, Gather
        except ImportError:
            current_app.logger.error("Twilio library not installed")
            return None

        response = VoiceResponse()

        # Welcome message
        response.say(
            "Welcome to Lab 4 All Water Flow, your water quality information system.",
            voice='alice',
            language='en-IN'
        )

        # Main menu with gather for DTMF input
        gather = Gather(
            num_digits=1,
            action=url_for('voice.handle_menu_selection', _external=True),
            method='POST',
            timeout=10
        )

        gather.say(
            "Press 1 for public water site information. "
            "Press 2 for residential water monitoring. "
            "Press 9 to repeat this menu.",
            voice='alice',
            language='en-IN'
        )

        response.append(gather)

        # If no input, redirect to welcome
        response.say("We didn't receive any input. Goodbye.", voice='alice', language='en-IN')
        response.hangup()

        return str(response)

    @staticmethod
    def generate_site_code_prompt(site_type='public'):
        """
        Generate prompt for site code input

        Args:
            site_type: 'public' or 'residential'

        Returns:
            TwiML XML string
        """
        try:
            from twilio.twiml.voice_response import VoiceResponse, Gather
        except ImportError:
            return None

        response = VoiceResponse()

        if site_type == 'public':
            gather = Gather(
                input='speech',
                action=url_for('voice.process_public_site', _external=True),
                method='POST',
                timeout=5,
                language='en-IN',
                speech_timeout='auto'
            )
            gather.say(
                "Please say the site code or site name. For example, say 'site code ABC 123' or 'Ganges River'.",
                voice='alice',
                language='en-IN'
            )
        else:  # residential
            gather = Gather(
                input='speech',
                action=url_for('voice.process_residential_site', _external=True),
                method='POST',
                timeout=5,
                language='en-IN',
                speech_timeout='auto'
            )
            gather.say(
                "Please say your device ID or location. For example, say 'device 456' or 'apartment 3 B'.",
                voice='alice',
                language='en-IN'
            )

        response.append(gather)

        # No input received
        response.say("No input received. Returning to main menu.", voice='alice', language='en-IN')
        response.redirect(url_for('voice.welcome', _external=True))

        return str(response)

    @staticmethod
    def generate_status_response(status_data, site_type='public'):
        """
        Generate TwiML for water quality status response

        Args:
            status_data: Status dictionary from WaterStatusService
            site_type: 'public' or 'residential'

        Returns:
            TwiML XML string
        """
        try:
            from twilio.twiml.voice_response import VoiceResponse
        except ImportError:
            return None

        from app.services.water_status_service import WaterStatusService

        response = VoiceResponse()

        # Get formatted voice response
        speech_text = WaterStatusService.format_voice_response(status_data)

        # Add pauses for better comprehension
        speech_text = speech_text.replace('. ', '. <break time="500ms"/> ')

        response.say(speech_text, voice='alice', language='en-IN')

        # Offer to repeat or return to menu
        response.pause(length=1)
        gather = response.gather(
            num_digits=1,
            action=url_for('voice.handle_repeat_menu', site_type=site_type, _external=True),
            method='POST',
            timeout=5
        )
        gather.say(
            "Press 1 to hear this report again. Press 2 to return to the main menu. Press 9 to end this call.",
            voice='alice',
            language='en-IN'
        )

        # Default action
        response.say("Thank you for using Lab 4 All Water Flow. Goodbye.", voice='alice', language='en-IN')
        response.hangup()

        return str(response)

    @staticmethod
    def generate_error_response(error_message, allow_retry=True):
        """
        Generate TwiML for error response

        Args:
            error_message: Error message to speak
            allow_retry: Whether to offer retry option

        Returns:
            TwiML XML string
        """
        try:
            from twilio.twiml.voice_response import VoiceResponse
        except ImportError:
            return None

        response = VoiceResponse()

        response.say(f"Sorry, {error_message}", voice='alice', language='en-IN')

        if allow_retry:
            response.pause(length=1)
            gather = response.gather(
                num_digits=1,
                action=url_for('voice.handle_error_retry', _external=True),
                method='POST',
                timeout=5
            )
            gather.say(
                "Press 1 to try again. Press 2 to return to the main menu.",
                voice='alice',
                language='en-IN'
            )

        response.say("Thank you for calling. Goodbye.", voice='alice', language='en-IN')
        response.hangup()

        return str(response)

    @staticmethod
    def generate_goodbye():
        """
        Generate goodbye TwiML

        Returns:
            TwiML XML string
        """
        try:
            from twilio.twiml.voice_response import VoiceResponse
        except ImportError:
            return None

        response = VoiceResponse()
        response.say(
            "Thank you for using Lab 4 All Water Flow water quality information system. "
            "For more information, visit our website. Goodbye.",
            voice='alice',
            language='en-IN'
        )
        response.hangup()

        return str(response)

    @staticmethod
    def generate_site_not_found(site_query, site_type='public'):
        """
        Generate TwiML for site not found error

        Args:
            site_query: The site code/name that wasn't found
            site_type: 'public' or 'residential'

        Returns:
            TwiML XML string
        """
        try:
            from twilio.twiml.voice_response import VoiceResponse
        except ImportError:
            return None

        response = VoiceResponse()

        if site_type == 'public':
            message = (
                f"Sorry, I could not find a water site matching '{site_query}'. "
                "Please check the site code or name and try again."
            )
        else:
            message = (
                f"Sorry, I could not find a residential device matching '{site_query}'. "
                "Please check the device ID or location and try again."
            )

        response.say(message, voice='alice', language='en-IN')

        # Offer to try again
        response.pause(length=1)
        gather = response.gather(
            num_digits=1,
            action=url_for('voice.handle_site_retry', site_type=site_type, _external=True),
            method='POST',
            timeout=5
        )
        gather.say(
            "Press 1 to enter a different site. Press 2 to return to the main menu.",
            voice='alice',
            language='en-IN'
        )

        response.redirect(url_for('voice.welcome', _external=True))

        return str(response)

    @staticmethod
    def generate_help_message():
        """
        Generate help message TwiML

        Returns:
            TwiML XML string
        """
        try:
            from twilio.twiml.voice_response import VoiceResponse
        except ImportError:
            return None

        response = VoiceResponse()

        response.say(
            "Lab 4 All Water Flow provides water quality information for public water sites "
            "and residential water monitoring devices. "
            "You can check the safety status, compliance with WHO and BIS standards, "
            "and get recommendations for water treatment. "
            "The system uses machine learning to predict water quality based on recent test results.",
            voice='alice',
            language='en-IN'
        )

        response.pause(length=1)
        response.redirect(url_for('voice.welcome', _external=True))

        return str(response)

    @staticmethod
    def generate_technical_difficulty():
        """
        Generate technical difficulty message TwiML

        Returns:
            TwiML XML string
        """
        try:
            from twilio.twiml.voice_response import VoiceResponse
        except ImportError:
            return None

        response = VoiceResponse()

        response.say(
            "We are experiencing technical difficulties at the moment. "
            "Please try again later or contact support. "
            "Thank you for your patience.",
            voice='alice',
            language='en-IN'
        )
        response.hangup()

        return str(response)

    @staticmethod
    def parse_speech_input(speech_result):
        """
        Parse speech recognition result to extract site code/name

        Args:
            speech_result: Speech recognition result from Twilio

        Returns:
            Cleaned string suitable for site lookup
        """
        if not speech_result:
            return None

        # Remove common filler words
        filler_words = ['site', 'code', 'device', 'id', 'number', 'apartment', 'flat']

        words = speech_result.lower().split()
        cleaned_words = [w for w in words if w not in filler_words]

        # Join and uppercase for site code matching
        cleaned = ' '.join(cleaned_words).strip().upper()

        return cleaned if cleaned else speech_result.upper()
