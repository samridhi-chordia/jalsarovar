"""
Data Validator Service
Validates imported water quality data before database insertion
"""
from datetime import datetime
from app import db
from app.models import WaterSample, Site


class DataValidator:
    """
    Validates imported water quality data before insertion into database.

    Performs validation on:
    - Required fields
    - Data types
    - Value ranges (pH, contamination levels)
    - Date formats
    - Foreign key references (sites, etc.)
    - WHO/BIS compliance limits
    """

    # Required fields for water quality data
    REQUIRED_FIELDS = [
        'sample_id',
        'site_name',
        'collection_date',
        'ph_value'
    ]

    # WHO guideline values for water quality parameters (mg/L)
    WHO_LIMITS = {
        'arsenic_mg_l': 0.01,
        'lead_mg_l': 0.01,
        'iron_mg_l': 0.3,
        'nitrate_mg_l': 50,
        'fluoride_mg_l': 1.5,
        'chloride_mg_l': 250,
        'sulfate_mg_l': 250,
        'total_dissolved_solids_mg_l': 1000,
        'hardness_mg_l': 500
    }

    # BIS (Bureau of Indian Standards) IS 10500:2012 limits
    BIS_LIMITS = {
        'arsenic_mg_l': 0.01,
        'lead_mg_l': 0.01,
        'iron_mg_l': 0.3,
        'nitrate_mg_l': 45,
        'fluoride_mg_l': 1.0,
        'chloride_mg_l': 250,
        'sulfate_mg_l': 200,
        'total_dissolved_solids_mg_l': 500,
        'hardness_mg_l': 300
    }

    def __init__(self):
        """Initialize validator"""
        self.errors = []
        self.warnings = []

    def validate_record(self, record, record_num):
        """
        Validate a single data record.

        Args:
            record (dict): Dictionary containing water quality data
            record_num (int): Row number in import file

        Returns:
            tuple: (is_valid, errors_list, warnings_list)
        """
        self.errors = []
        self.warnings = []

        # Run validation checks
        self._validate_required_fields(record, record_num)
        self._validate_data_types(record, record_num)
        self._validate_value_ranges(record, record_num)
        self._validate_dates(record, record_num)
        self._validate_references(record, record_num)
        self._check_who_limits(record, record_num)
        self._check_bis_limits(record, record_num)

        is_valid = len(self.errors) == 0
        return is_valid, self.errors.copy(), self.warnings.copy()

    def _validate_required_fields(self, record, record_num):
        """Check that all required fields are present and not empty"""
        for field in self.REQUIRED_FIELDS:
            if field not in record or record[field] is None or str(record[field]).strip() == '':
                self.errors.append({
                    'row': record_num,
                    'field': field,
                    'error': f'Required field "{field}" is missing or empty',
                    'value': record.get(field, 'N/A')
                })

    def _validate_data_types(self, record, record_num):
        """Validate that numeric fields contain valid numbers"""
        numeric_fields = [
            'ph_value', 'temperature_c', 'turbidity_ntu',
            'arsenic_mg_l', 'lead_mg_l', 'iron_mg_l', 'nitrate_mg_l',
            'fluoride_mg_l', 'chloride_mg_l', 'sulfate_mg_l',
            'total_dissolved_solids_mg_l', 'hardness_mg_l',
            'conductivity_us_cm', 'dissolved_oxygen_mg_l'
        ]

        for field in numeric_fields:
            if field in record and record[field] is not None:
                try:
                    value = str(record[field]).strip()
                    if value != '':
                        float(value)
                except (ValueError, TypeError):
                    self.errors.append({
                        'row': record_num,
                        'field': field,
                        'error': f'Invalid numeric value',
                        'value': record[field]
                    })

    def _validate_value_ranges(self, record, record_num):
        """Validate that values are within acceptable ranges"""

        # pH must be between 0 and 14
        if 'ph_value' in record and record['ph_value'] is not None:
            try:
                ph = float(record['ph_value'])
                if ph < 0 or ph > 14:
                    self.errors.append({
                        'row': record_num,
                        'field': 'ph_value',
                        'error': 'pH must be between 0 and 14',
                        'value': ph
                    })
                elif ph < 6.5 or ph > 8.5:
                    self.warnings.append({
                        'row': record_num,
                        'field': 'ph_value',
                        'warning': 'pH outside WHO recommended range (6.5-8.5)',
                        'value': ph
                    })
            except (ValueError, TypeError):
                pass  # Already caught in _validate_data_types

        # Temperature should be reasonable (-10°C to 50°C)
        if 'temperature_c' in record and record['temperature_c'] is not None:
            try:
                temp = float(record['temperature_c'])
                if temp < -10 or temp > 50:
                    self.warnings.append({
                        'row': record_num,
                        'field': 'temperature_c',
                        'warning': 'Temperature seems unusual (expected -10°C to 50°C)',
                        'value': temp
                    })
            except (ValueError, TypeError):
                pass

        # Turbidity cannot be negative
        if 'turbidity_ntu' in record and record['turbidity_ntu'] is not None:
            try:
                turbidity = float(record['turbidity_ntu'])
                if turbidity < 0:
                    self.errors.append({
                        'row': record_num,
                        'field': 'turbidity_ntu',
                        'error': 'Turbidity cannot be negative',
                        'value': turbidity
                    })
            except (ValueError, TypeError):
                pass

        # Check for negative values in concentration fields
        concentration_fields = [
            'arsenic_mg_l', 'lead_mg_l', 'iron_mg_l', 'nitrate_mg_l',
            'fluoride_mg_l', 'chloride_mg_l', 'sulfate_mg_l',
            'total_dissolved_solids_mg_l', 'hardness_mg_l'
        ]

        for field in concentration_fields:
            if field in record and record[field] is not None:
                try:
                    value = float(record[field])
                    if value < 0:
                        self.errors.append({
                            'row': record_num,
                            'field': field,
                            'error': 'Concentration cannot be negative',
                            'value': value
                        })
                except (ValueError, TypeError):
                    pass

    def _validate_dates(self, record, record_num):
        """Validate date fields"""
        date_fields = ['collection_date', 'analysis_date']

        for field in date_fields:
            if field in record and record[field] is not None:
                value = record[field]

                # Skip if empty string
                if isinstance(value, str) and value.strip() == '':
                    continue

                # If already a datetime object, check if valid
                if isinstance(value, datetime):
                    if value > datetime.now():
                        self.warnings.append({
                            'row': record_num,
                            'field': field,
                            'warning': 'Date is in the future',
                            'value': value.isoformat()
                        })
                    continue

                # Try to parse string date
                try:
                    # Try common date formats
                    date_formats = [
                        '%Y-%m-%d',
                        '%d-%m-%Y',
                        '%d/%m/%Y',
                        '%Y/%m/%d',
                        '%Y-%m-%d %H:%M:%S',
                        '%d-%m-%Y %H:%M:%S'
                    ]

                    parsed_date = None
                    for fmt in date_formats:
                        try:
                            parsed_date = datetime.strptime(str(value).strip(), fmt)
                            break
                        except ValueError:
                            continue

                    if parsed_date is None:
                        self.errors.append({
                            'row': record_num,
                            'field': field,
                            'error': 'Invalid date format (expected YYYY-MM-DD)',
                            'value': value
                        })
                    elif parsed_date > datetime.now():
                        self.warnings.append({
                            'row': record_num,
                            'field': field,
                            'warning': 'Date is in the future',
                            'value': value
                        })

                except Exception as e:
                    self.errors.append({
                        'row': record_num,
                        'field': field,
                        'error': f'Invalid date: {str(e)}',
                        'value': value
                    })

    def _validate_references(self, record, record_num):
        """Validate foreign key references (e.g., site names)"""

        # Check if site exists
        if 'site_name' in record and record['site_name']:
            site_name = str(record['site_name']).strip()
            site = Site.query.filter_by(name=site_name).first()

            if not site:
                self.warnings.append({
                    'row': record_num,
                    'field': 'site_name',
                    'warning': f'Site "{site_name}" not found in database. Will be created automatically.',
                    'value': site_name
                })

    def _check_who_limits(self, record, record_num):
        """Check values against WHO guidelines"""
        for field, limit in self.WHO_LIMITS.items():
            if field in record and record[field] is not None:
                try:
                    value = float(record[field])
                    if value > limit:
                        self.warnings.append({
                            'row': record_num,
                            'field': field,
                            'warning': f'Exceeds WHO guideline of {limit} mg/L',
                            'value': value,
                            'limit_type': 'WHO'
                        })
                except (ValueError, TypeError):
                    pass

    def _check_bis_limits(self, record, record_num):
        """Check values against BIS (Bureau of Indian Standards) limits"""
        for field, limit in self.BIS_LIMITS.items():
            if field in record and record[field] is not None:
                try:
                    value = float(record[field])
                    if value > limit:
                        self.warnings.append({
                            'row': record_num,
                            'field': field,
                            'warning': f'Exceeds BIS (IS 10500:2012) limit of {limit} mg/L',
                            'value': value,
                            'limit_type': 'BIS'
                        })
                except (ValueError, TypeError):
                    pass

    def validate_batch(self, records):
        """
        Validate multiple records at once.

        Args:
            records (list): List of record dictionaries

        Returns:
            dict: Summary of validation results {
                'total': total records,
                'valid': valid count,
                'invalid': invalid count,
                'warnings': warning count,
                'errors': list of all errors,
                'warnings_list': list of all warnings
            }
        """
        all_errors = []
        all_warnings = []
        valid_count = 0
        invalid_count = 0

        for idx, record in enumerate(records, start=1):
            is_valid, errors, warnings = self.validate_record(record, idx)

            if is_valid:
                valid_count += 1
            else:
                invalid_count += 1

            all_errors.extend(errors)
            all_warnings.extend(warnings)

        return {
            'total': len(records),
            'valid': valid_count,
            'invalid': invalid_count,
            'warning_count': len(all_warnings),
            'errors': all_errors,
            'warnings': all_warnings
        }

    def get_validation_summary(self):
        """
        Get human-readable summary of last validation.

        Returns:
            str: Summary text
        """
        if not self.errors and not self.warnings:
            return "✓ All validation checks passed"

        summary = []
        if self.errors:
            summary.append(f"✗ {len(self.errors)} error(s) found")
        if self.warnings:
            summary.append(f"⚠ {len(self.warnings)} warning(s)")

        return " | ".join(summary)
