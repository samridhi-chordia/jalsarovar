"""
Water Status Service
Queries and formats water quality data for voice agent responses.
Handles both public water sites and residential IoT monitoring.
"""
from datetime import datetime, timedelta
from flask import current_app
from sqlalchemy import desc

from app import db
from app.models.site import Site
from app.models.water_sample import WaterSample
from app.models.analysis import Analysis
from app.models.residential_site import ResidentialSite, ResidentialMeasurement, ResidentialAlert


class WaterStatusService:
    """Service for retrieving and formatting water quality status"""

    @staticmethod
    def find_public_site(query):
        """
        Find a public water site by code or name (fuzzy matching)

        Args:
            query: Site code or partial name

        Returns:
            Site object or None
        """
        query = query.strip().upper()

        # Try exact site_code match first
        site = Site.query.filter_by(site_code=query).first()
        if site:
            return site

        # Try partial name match (case-insensitive)
        site = Site.query.filter(Site.site_name.ilike(f'%{query}%')).first()
        if site:
            return site

        # Try source_site_id match (for imported data)
        site = Site.query.filter_by(source_site_id=query).first()
        return site

    @staticmethod
    def find_residential_site(query):
        """
        Find a residential site by device_id or name

        Args:
            query: Device ID or partial name

        Returns:
            ResidentialSite object or None
        """
        query = query.strip().upper()

        # Try exact device_id match
        site = ResidentialSite.query.filter_by(device_id=query).first()
        if site:
            return site

        # Try partial location match
        site = ResidentialSite.query.filter(
            ResidentialSite.location.ilike(f'%{query}%')
        ).first()
        return site

    @staticmethod
    def get_public_site_status(site_code):
        """
        Get water quality status for a public site

        Args:
            site_code: Site code or name

        Returns:
            dict with status information or None if not found
        """
        site = WaterStatusService.find_public_site(site_code)
        if not site:
            return None

        # Get most recent analysis
        analysis = Analysis.query.filter_by(site_id=site.id).order_by(
            desc(Analysis.created_at)
        ).first()

        if not analysis:
            return {
                'site_code': site.site_code,
                'site_name': site.site_name,
                'status': 'no_data',
                'message': f"No water quality data available for {site.site_name}"
            }

        # Get the water sample
        sample = WaterSample.query.get(analysis.sample_id)

        # Format status response
        response = {
            'site_code': site.site_code,
            'site_name': site.site_name,
            'location': site.location,
            'status': 'safe' if analysis.is_safe else 'unsafe',
            'is_safe': analysis.is_safe,
            'sample_date': sample.collection_date.strftime('%B %d, %Y') if sample and sample.collection_date else 'Unknown',
            'analysis_date': analysis.created_at.strftime('%B %d, %Y'),
            'ml_prediction': analysis.ml_prediction,
            'confidence': round(analysis.ml_confidence * 100, 1) if analysis.ml_confidence else None,
            'who_compliant': analysis.who_compliant,
            'bis_compliant': analysis.bis_compliant,
            'risk_level': analysis.risk_level,
            'contaminants': [],
            'recommendations': analysis.recommendations or 'No specific recommendations available'
        }

        # Add key contaminants if unsafe
        if not analysis.is_safe and sample:
            from app.models.test_result import TestResult
            test_results = TestResult.query.filter_by(sample_id=sample.id).all()

            # Find parameters that exceed limits
            for result in test_results:
                if result.exceeds_limit:
                    response['contaminants'].append({
                        'parameter': result.parameter_name,
                        'value': result.value,
                        'unit': result.unit if hasattr(result, 'unit') else ''
                    })

        return response

    @staticmethod
    def get_residential_site_status(device_id):
        """
        Get water quality status for a residential site

        Args:
            device_id: Device ID or location

        Returns:
            dict with status information or None if not found
        """
        site = WaterStatusService.find_residential_site(device_id)
        if not site:
            return None

        # Get most recent measurement
        measurement = ResidentialMeasurement.query.filter_by(
            residential_site_id=site.id
        ).order_by(desc(ResidentialMeasurement.measured_at)).first()

        if not measurement:
            return {
                'device_id': site.device_id,
                'location': site.location,
                'status': 'no_data',
                'message': f"No measurements available for device {site.device_id}"
            }

        # Get recent alerts (last 7 days)
        recent_alerts = ResidentialAlert.query.filter(
            ResidentialAlert.residential_site_id == site.id,
            ResidentialAlert.created_at >= datetime.utcnow() - timedelta(days=7)
        ).order_by(desc(ResidentialAlert.created_at)).limit(5).all()

        response = {
            'device_id': site.device_id,
            'location': site.location,
            'status': 'safe' if measurement.is_safe else 'unsafe',
            'is_safe': measurement.is_safe,
            'measurement_date': measurement.measured_at.strftime('%B %d, %Y %I:%M %p'),
            'tds': measurement.tds,
            'ph': measurement.ph,
            'turbidity': measurement.turbidity,
            'temperature': measurement.temperature,
            'alert_count': len(recent_alerts),
            'recent_alerts': [],
            'recommendations': 'Water is safe for consumption' if measurement.is_safe else 'Water quality issues detected. Consider filtration or alternative source.'
        }

        # Add recent alert details
        for alert in recent_alerts:
            response['recent_alerts'].append({
                'severity': alert.severity,
                'parameter': alert.parameter_affected,
                'message': alert.alert_message,
                'date': alert.created_at.strftime('%B %d, %I:%M %p')
            })

        return response

    @staticmethod
    def format_sms_response(status_data):
        """
        Format status data for SMS (160 character limit awareness)

        Args:
            status_data: Status dict from get_public_site_status or get_residential_site_status

        Returns:
            Formatted SMS text
        """
        if not status_data:
            return "Site not found. Please check the site code and try again."

        if status_data['status'] == 'no_data':
            return status_data['message']

        # Check if it's residential or public
        is_residential = 'device_id' in status_data

        if is_residential:
            # Residential format
            status_emoji = "✓" if status_data['is_safe'] else "⚠"
            return (
                f"{status_emoji} {status_data['location']}\n"
                f"Status: {'SAFE' if status_data['is_safe'] else 'UNSAFE'}\n"
                f"TDS: {status_data['tds']} ppm\n"
                f"pH: {status_data['ph']}\n"
                f"Measured: {status_data['measurement_date']}\n"
                f"{status_data['recommendations']}"
            )
        else:
            # Public site format
            status_emoji = "✓" if status_data['is_safe'] else "⚠"
            confidence_str = f" ({status_data['confidence']}%)" if status_data['confidence'] else ""

            msg = (
                f"{status_emoji} {status_data['site_name']}\n"
                f"Status: {'SAFE' if status_data['is_safe'] else 'UNSAFE'}{confidence_str}\n"
                f"WHO: {'✓' if status_data['who_compliant'] else '✗'} | "
                f"BIS: {'✓' if status_data['bis_compliant'] else '✗'}\n"
            )

            if status_data['contaminants']:
                msg += "Issues: " + ", ".join([c['parameter'] for c in status_data['contaminants'][:3]]) + "\n"

            msg += f"Tested: {status_data['sample_date']}"

            return msg

    @staticmethod
    def format_voice_response(status_data):
        """
        Format status data for voice call (spoken text)

        Args:
            status_data: Status dict from get_public_site_status or get_residential_site_status

        Returns:
            Formatted text for text-to-speech
        """
        if not status_data:
            return "Sorry, I could not find the requested site. Please check the site code and try again."

        if status_data['status'] == 'no_data':
            return status_data['message']

        # Check if it's residential or public
        is_residential = 'device_id' in status_data

        if is_residential:
            # Residential format
            speech = (
                f"Water quality report for {status_data['location']}. "
                f"Current status: {'Safe' if status_data['is_safe'] else 'Unsafe'}. "
                f"Total dissolved solids: {status_data['tds']} parts per million. "
                f"pH level: {status_data['ph']}. "
            )

            if status_data['turbidity'] is not None:
                speech += f"Turbidity: {status_data['turbidity']} NTU. "

            speech += f"Last measured on {status_data['measurement_date']}. "

            if status_data['alert_count'] > 0:
                speech += f"There are {status_data['alert_count']} recent alerts for this device. "

            speech += status_data['recommendations']

        else:
            # Public site format
            speech = (
                f"Water quality report for {status_data['site_name']}. "
                f"Current status: {'Safe for consumption' if status_data['is_safe'] else 'Not safe for consumption'}. "
            )

            if status_data['confidence']:
                speech += f"Confidence level: {status_data['confidence']} percent. "

            speech += (
                f"{'Compliant' if status_data['who_compliant'] else 'Not compliant'} with WHO standards. "
                f"{'Compliant' if status_data['bis_compliant'] else 'Not compliant'} with BIS standards. "
            )

            if status_data['contaminants']:
                contaminant_names = [c['parameter'] for c in status_data['contaminants'][:3]]
                speech += f"Detected contaminants include: {', '.join(contaminant_names)}. "

            speech += f"Sample tested on {status_data['sample_date']}. "
            speech += status_data['recommendations']

        return speech

    @staticmethod
    def format_whatsapp_response(status_data):
        """
        Format status data for WhatsApp (supports richer formatting)

        Args:
            status_data: Status dict from get_public_site_status or get_residential_site_status

        Returns:
            Formatted WhatsApp message with markdown
        """
        if not status_data:
            return "🔍 *Site not found*\nPlease check the site code and try again."

        if status_data['status'] == 'no_data':
            return f"ℹ️ {status_data['message']}"

        # Check if it's residential or public
        is_residential = 'device_id' in status_data

        if is_residential:
            # Residential format
            status_emoji = "✅" if status_data['is_safe'] else "⚠️"
            msg = (
                f"{status_emoji} *Water Quality Report*\n"
                f"📍 {status_data['location']}\n"
                f"🆔 Device: {status_data['device_id']}\n\n"
                f"*Status:* {'SAFE ✓' if status_data['is_safe'] else 'UNSAFE ✗'}\n\n"
                f"*Parameters:*\n"
                f"• TDS: {status_data['tds']} ppm\n"
                f"• pH: {status_data['ph']}\n"
            )

            if status_data['turbidity'] is not None:
                msg += f"• Turbidity: {status_data['turbidity']} NTU\n"
            if status_data['temperature'] is not None:
                msg += f"• Temperature: {status_data['temperature']}°C\n"

            msg += f"\n📅 Measured: {status_data['measurement_date']}\n"

            if status_data['alert_count'] > 0:
                msg += f"\n⚠️ *{status_data['alert_count']} Recent Alerts*\n"
                for alert in status_data['recent_alerts'][:3]:
                    msg += f"• {alert['severity']}: {alert['parameter']} - {alert['date']}\n"

            msg += f"\n💡 {status_data['recommendations']}"

        else:
            # Public site format
            status_emoji = "✅" if status_data['is_safe'] else "⚠️"
            confidence_str = f" ({status_data['confidence']}%)" if status_data['confidence'] else ""

            msg = (
                f"{status_emoji} *Water Quality Report*\n"
                f"📍 {status_data['site_name']}\n"
                f"🆔 Site: {status_data['site_code']}\n\n"
                f"*Status:* {'SAFE ✓' if status_data['is_safe'] else 'UNSAFE ✗'}{confidence_str}\n"
                f"*ML Prediction:* {status_data['ml_prediction']}\n\n"
                f"*Compliance:*\n"
                f"• WHO: {'✓ Compliant' if status_data['who_compliant'] else '✗ Non-compliant'}\n"
                f"• BIS: {'✓ Compliant' if status_data['bis_compliant'] else '✗ Non-compliant'}\n"
            )

            if status_data['risk_level']:
                msg += f"• Risk Level: {status_data['risk_level']}\n"

            if status_data['contaminants']:
                msg += "\n*Detected Contaminants:*\n"
                for c in status_data['contaminants'][:5]:
                    msg += f"• {c['parameter']}: {c['value']} {c['unit']}\n"

            msg += f"\n📅 Sample Date: {status_data['sample_date']}\n"
            msg += f"📊 Analysis Date: {status_data['analysis_date']}\n"
            msg += f"\n💡 {status_data['recommendations']}"

        return msg
