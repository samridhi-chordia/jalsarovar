"""
Intervention Analyzer Service
Analyzes effectiveness of water treatment interventions
Ported from jalsarovar_RELEASE and adapted for lab4all_webapp model structure
"""
import json
from app.models.intervention import Intervention, TreatmentMethod
from app.models.water_sample import WaterSample
from app.models.test_result import TestResult
from app import db
from sqlalchemy import func


class InterventionAnalyzer:
    """
    Service for analyzing intervention effectiveness and providing recommendations.

    Features:
    - Pre/post quality comparison
    - Statistical significance testing
    - ROI calculation
    - Treatment recommendations by contamination type
    """

    # Treatment recommendations by contamination type
    CONTAMINATION_TREATMENTS = {
        'physical': ['sand_filtration', 'sedimentation', 'aeration', 'membrane_filtration'],
        'bacterial': ['chlorination', 'uv_disinfection', 'ozonation', 'boiling'],
        'chemical': ['activated_carbon', 'reverse_osmosis', 'ion_exchange', 'chemical_precipitation'],
        'none': [],
        'runoff': ['sand_filtration', 'sedimentation', 'constructed_wetland'],
        'sewage': ['chlorination', 'biological_treatment', 'activated_sludge'],
        'salt': ['reverse_osmosis', 'desalination', 'electrodialysis'],
        'corrosion': ['ph_adjustment', 'corrosion_inhibitors', 'pipe_replacement'],
        'decay': ['rechlorination', 'flushing', 'reservoir_management']
    }

    def __init__(self):
        pass

    def analyze_intervention(self, intervention_id):
        """
        Comprehensive analysis of a single intervention's effectiveness.

        Returns dict with:
        - intervention details
        - improvement_metrics
        - cost_effectiveness
        - recommendations
        """
        intervention = Intervention.query.get(intervention_id)
        if not intervention:
            return {'error': 'Intervention not found'}

        analysis = {
            'intervention': self._intervention_to_dict(intervention),
            'improvement_metrics': {},
            'cost_effectiveness': {},
            'recommendations': []
        }

        # Calculate improvement from before/after values
        improvement_pct = intervention.calculate_effectiveness()
        if improvement_pct is not None:
            analysis['improvement_metrics']['improvement_percentage'] = round(improvement_pct, 2)
            analysis['improvement_metrics']['parameter_targeted'] = intervention.parameter_targeted
            analysis['improvement_metrics']['before_value'] = intervention.before_value
            analysis['improvement_metrics']['after_value'] = intervention.after_value

            # Determine effectiveness rating
            if improvement_pct > 30:
                analysis['improvement_metrics']['effectiveness'] = 'Highly Effective'
            elif improvement_pct > 10:
                analysis['improvement_metrics']['effectiveness'] = 'Moderately Effective'
            elif improvement_pct > 0:
                analysis['improvement_metrics']['effectiveness'] = 'Marginally Effective'
            else:
                analysis['improvement_metrics']['effectiveness'] = 'Not Effective'

        # Cost effectiveness (improvement per unit cost)
        total_cost = self._get_total_cost(intervention)
        if total_cost and improvement_pct and improvement_pct > 0:
            cost_per_percent_improvement = total_cost / improvement_pct
            analysis['cost_effectiveness'] = {
                'total_cost_inr': total_cost,
                'cost_per_percent_improvement': round(cost_per_percent_improvement, 2),
                'value_rating': self._rate_cost_effectiveness(cost_per_percent_improvement)
            }

        # Recommendations
        if improvement_pct is None or improvement_pct < 20:
            analysis['recommendations'].append(
                "Consider additional or alternative treatment methods"
            )

        if intervention.follow_up_required:
            analysis['recommendations'].append(
                f"Follow-up scheduled for {intervention.follow_up_date}" if intervention.follow_up_date else "Follow-up required - schedule follow-up date"
            )

        if intervention.effectiveness_rating and intervention.effectiveness_rating < 5:
            analysis['recommendations'].append(
                "Low effectiveness rating - consider reviewing treatment protocol"
            )

        return analysis

    def _intervention_to_dict(self, intervention):
        """Convert intervention to dictionary"""
        return {
            'id': intervention.id,
            'intervention_date': intervention.intervention_date.isoformat() if intervention.intervention_date else None,
            'intervention_type': intervention.intervention_type,
            'description': intervention.description,
            'status': intervention.status,
            'parameter_targeted': intervention.parameter_targeted,
            'before_value': intervention.before_value,
            'after_value': intervention.after_value,
            'improvement_percent': intervention.improvement_percent,
            'effectiveness_rating': intervention.effectiveness_rating,
            'treatment_method': intervention.treatment_method.method_name if intervention.treatment_method else None,
            'site_id': intervention.site_id,
            'total_cost_inr': self._get_total_cost(intervention)
        }

    def _get_total_cost(self, intervention):
        """Calculate total cost of intervention"""
        total = 0
        if intervention.actual_cost_inr:
            total += intervention.actual_cost_inr
        if intervention.labor_cost_inr:
            total += intervention.labor_cost_inr
        if intervention.material_cost_inr:
            total += intervention.material_cost_inr
        return total if total > 0 else None

    def _rate_cost_effectiveness(self, cost_per_percent):
        """Rate cost effectiveness on a simple scale (INR)"""
        if cost_per_percent < 500:
            return 'Excellent'
        elif cost_per_percent < 2000:
            return 'Good'
        elif cost_per_percent < 5000:
            return 'Fair'
        else:
            return 'Poor'

    def get_effectiveness_by_treatment_method(self):
        """
        Calculate effectiveness rates for all treatment methods based on historical interventions.

        Returns list of treatment methods with their success rates.
        """
        results = []

        treatment_methods = TreatmentMethod.query.filter_by(is_active=True).all()

        for method in treatment_methods:
            # Get all completed interventions using this method
            completed = Intervention.query.filter_by(
                treatment_method_id=method.id,
                status='completed'
            ).all()

            if not completed:
                results.append({
                    'treatment_method': method.method_name,
                    'method_code': method.method_code,
                    'total_interventions': 0,
                    'successful_interventions': 0,
                    'success_rate': 0,
                    'average_improvement': None,
                    'average_cost_inr': None
                })
                continue

            # Count successful ones (effectiveness_rating >= 7 or improvement > 20%)
            successful = sum(1 for i in completed if self._is_successful(i))

            # Calculate averages
            improvements = [i.improvement_percent for i in completed if i.improvement_percent is not None]
            avg_improvement = sum(improvements) / len(improvements) if improvements else None

            costs = [self._get_total_cost(i) for i in completed]
            costs = [c for c in costs if c is not None]
            avg_cost = sum(costs) / len(costs) if costs else None

            success_rate = (successful / len(completed)) * 100

            results.append({
                'treatment_method': method.method_name,
                'method_code': method.method_code,
                'total_interventions': len(completed),
                'successful_interventions': successful,
                'success_rate': round(success_rate, 1),
                'average_improvement': round(avg_improvement, 2) if avg_improvement else None,
                'average_cost_inr': round(avg_cost, 2) if avg_cost else None
            })

        # Sort by success rate descending
        results.sort(key=lambda x: x['success_rate'], reverse=True)

        return results

    def _is_successful(self, intervention):
        """Determine if an intervention was successful"""
        # Check effectiveness rating if available
        if intervention.effectiveness_rating and intervention.effectiveness_rating >= 7:
            return True
        # Check improvement percentage
        if intervention.improvement_percent and intervention.improvement_percent > 20:
            return True
        return False

    def recommend_treatment(self, contamination_type, budget_inr=None, site_type=None):
        """
        Recommend most effective treatment methods for a specific contamination type.

        Args:
            contamination_type: String like 'physical', 'bacterial', 'chemical', 'runoff', etc.
            budget_inr: Optional maximum budget constraint in INR
            site_type: Optional site type (pond, lake, tank, etc.)

        Returns:
            List of recommended treatment methods sorted by effectiveness
        """
        # Normalize contamination type
        contamination_type = contamination_type.lower().strip()

        # Get treatment method codes for this contamination type
        suitable_codes = self.CONTAMINATION_TREATMENTS.get(contamination_type, [])

        if not suitable_codes:
            return {
                'contamination_type': contamination_type,
                'recommendations': [],
                'message': f'No treatment methods found for {contamination_type}'
            }

        # Get all active treatment methods
        methods = TreatmentMethod.query.filter_by(is_active=True).all()

        recommendations = []
        for method in methods:
            # Check if method is suitable for this contamination
            method_code_lower = (method.method_code or '').lower()
            method_name_lower = method.method_name.lower()

            is_suitable = any(
                code in method_code_lower or code.replace('_', ' ') in method_name_lower
                for code in suitable_codes
            )

            # Also check contamination_types field if available
            if method.contamination_types:
                try:
                    types_list = json.loads(method.contamination_types) if isinstance(method.contamination_types, str) else method.contamination_types
                    if contamination_type in [t.lower() for t in types_list]:
                        is_suitable = True
                except (json.JSONDecodeError, TypeError):
                    pass

            if not is_suitable:
                continue

            # Skip if over budget
            if budget_inr and method.estimated_cost_min_inr and method.estimated_cost_min_inr > budget_inr:
                continue

            # Get historical effectiveness
            effectiveness_data = self._get_method_effectiveness(method.id)

            rec = {
                'treatment_method': method.method_name,
                'method_code': method.method_code,
                'description': method.description,
                'cost_range_inr': self._format_cost_range(method),
                'implementation_days': method.implementation_time_days,
                'time_to_effect_days': method.time_to_effect_days,
                'duration_months': method.duration_effectiveness_months,
                'requires_specialist': method.requires_specialist,
                'requires_equipment': method.requires_equipment,
                'expected_effectiveness': method.average_effectiveness_percent,
                'historical_uses': effectiveness_data['intervention_count'],
                'historical_success_rate': effectiveness_data['effectiveness_rate'],
                'average_improvement': effectiveness_data['average_improvement']
            }

            recommendations.append(rec)

        # Sort by expected effectiveness and historical success
        recommendations.sort(
            key=lambda x: (
                x['expected_effectiveness'] or 0,
                x['historical_success_rate'] or 0,
                x['historical_uses'] or 0
            ),
            reverse=True
        )

        return {
            'contamination_type': contamination_type,
            'budget_inr': budget_inr,
            'recommendations': recommendations,
            'count': len(recommendations)
        }

    def _format_cost_range(self, method):
        """Format cost range for display"""
        min_cost = method.estimated_cost_min_inr
        max_cost = method.estimated_cost_max_inr

        if min_cost and max_cost:
            return f"Rs {min_cost:,.0f} - Rs {max_cost:,.0f}"
        elif min_cost:
            return f"Rs {min_cost:,.0f}+"
        elif max_cost:
            return f"Up to Rs {max_cost:,.0f}"
        elif method.cost_per_kl:
            return f"Rs {method.cost_per_kl:,.0f}/KL"
        return "Cost not specified"

    def _get_method_effectiveness(self, treatment_method_id):
        """Get effectiveness metrics for a specific treatment method"""
        interventions = Intervention.query.filter_by(
            treatment_method_id=treatment_method_id,
            status='completed'
        ).all()

        if not interventions:
            return {
                'effectiveness_rate': 0,
                'intervention_count': 0,
                'average_improvement': None
            }

        successful = sum(1 for i in interventions if self._is_successful(i))
        improvements = [i.improvement_percent for i in interventions if i.improvement_percent]

        return {
            'effectiveness_rate': round((successful / len(interventions)) * 100, 1) if interventions else 0,
            'intervention_count': len(interventions),
            'average_improvement': round(sum(improvements) / len(improvements), 2) if improvements else None
        }

    def get_intervention_summary_stats(self):
        """
        Get overall summary statistics for all interventions in the system.

        Returns:
            Dict with summary metrics
        """
        total = Intervention.query.count()
        completed = Intervention.query.filter_by(status='completed').count()
        in_progress = Intervention.query.filter_by(status='in_progress').count()
        planned = Intervention.query.filter_by(status='planned').count()
        verified = Intervention.query.filter_by(status='verified').count()

        # Get successful interventions
        completed_list = Intervention.query.filter_by(status='completed').all()
        successful_count = sum(1 for i in completed_list if self._is_successful(i))

        # Calculate average metrics
        avg_improvement = None
        avg_cost = None
        total_cost = 0

        if completed_list:
            improvements = [i.improvement_percent for i in completed_list if i.improvement_percent]
            if improvements:
                avg_improvement = sum(improvements) / len(improvements)

            costs = [self._get_total_cost(i) for i in completed_list]
            costs = [c for c in costs if c is not None]
            if costs:
                avg_cost = sum(costs) / len(costs)
                total_cost = sum(costs)

        return {
            'total_interventions': total,
            'by_status': {
                'planned': planned,
                'in_progress': in_progress,
                'completed': completed,
                'verified': verified
            },
            'successful_interventions': successful_count,
            'success_rate': round((successful_count / completed) * 100, 1) if completed > 0 else 0,
            'average_improvement': round(avg_improvement, 2) if avg_improvement else None,
            'average_cost_inr': round(avg_cost, 2) if avg_cost else None,
            'total_cost_inr': round(total_cost, 2) if total_cost else 0
        }

    def calculate_roi(self, intervention_id):
        """
        Calculate Return on Investment for an intervention.

        ROI = (Quality Improvement Value - Cost) / Cost * 100

        Note: This is a simplified calculation using estimated health impact value.
        """
        intervention = Intervention.query.get(intervention_id)
        if not intervention or intervention.status not in ('completed', 'verified'):
            return None

        total_cost = self._get_total_cost(intervention)
        improvement_pct = intervention.improvement_percent or intervention.calculate_effectiveness()

        if not total_cost or not improvement_pct:
            return None

        # Simplified: assume each 1% improvement is worth Rs 500
        # In practice, this should be based on health impact, DALY analysis, etc.
        improvement_value = improvement_pct * 500

        roi = ((improvement_value - total_cost) / total_cost) * 100

        return {
            'intervention_id': intervention_id,
            'total_cost_inr': total_cost,
            'improvement_percentage': improvement_pct,
            'estimated_value_inr': improvement_value,
            'roi_percentage': round(roi, 2),
            'note': 'Simplified calculation. Actual ROI should consider health outcomes and long-term benefits.'
        }

    def get_site_intervention_history(self, site_id, limit=10):
        """
        Get intervention history for a specific site.

        Returns list of interventions with analysis.
        """
        interventions = Intervention.query.filter_by(site_id=site_id)\
            .order_by(Intervention.intervention_date.desc())\
            .limit(limit)\
            .all()

        return [self._intervention_to_dict(i) for i in interventions]

    def get_parameter_intervention_stats(self, parameter):
        """
        Get intervention statistics for a specific water quality parameter.

        Args:
            parameter: Water quality parameter (ph, turbidity, tds, etc.)

        Returns:
            Dict with intervention stats for this parameter
        """
        interventions = Intervention.query.filter_by(
            parameter_targeted=parameter,
            status='completed'
        ).all()

        if not interventions:
            return {
                'parameter': parameter,
                'total_interventions': 0,
                'message': f'No completed interventions targeting {parameter}'
            }

        successful = sum(1 for i in interventions if self._is_successful(i))
        improvements = [i.improvement_percent for i in interventions if i.improvement_percent]

        # Group by treatment method
        method_stats = {}
        for i in interventions:
            method_name = i.treatment_method.method_name if i.treatment_method else 'Unknown'
            if method_name not in method_stats:
                method_stats[method_name] = {'count': 0, 'improvements': []}
            method_stats[method_name]['count'] += 1
            if i.improvement_percent:
                method_stats[method_name]['improvements'].append(i.improvement_percent)

        # Calculate averages per method
        method_results = []
        for method, data in method_stats.items():
            avg_imp = sum(data['improvements']) / len(data['improvements']) if data['improvements'] else None
            method_results.append({
                'treatment_method': method,
                'intervention_count': data['count'],
                'average_improvement': round(avg_imp, 2) if avg_imp else None
            })

        method_results.sort(key=lambda x: x['average_improvement'] or 0, reverse=True)

        return {
            'parameter': parameter,
            'total_interventions': len(interventions),
            'successful_interventions': successful,
            'success_rate': round((successful / len(interventions)) * 100, 1),
            'average_improvement': round(sum(improvements) / len(improvements), 2) if improvements else None,
            'by_treatment_method': method_results
        }

    # WHO/BIS water quality thresholds
    THRESHOLDS = {
        'ph': {'min': 6.5, 'max': 8.5, 'param': 'pH', 'type': 'chemical'},
        'turbidity_ntu': {'max': 5.0, 'param': 'turbidity', 'type': 'physical'},
        'tds_ppm': {'max': 500.0, 'param': 'TDS', 'type': 'chemical'},
        'iron_mg_l': {'max': 0.3, 'param': 'iron', 'type': 'chemical'},
        'chloride_mg_l': {'max': 250.0, 'param': 'chloride', 'type': 'chemical'},
        'total_coliform_mpn': {'max': 0, 'param': 'coliform', 'type': 'bacterial'},
        'free_chlorine_mg_l': {'min': 0.2, 'max': 5.0, 'param': 'chlorine', 'type': 'decay'},
    }

    def detect_contamination_from_test(self, test_result):
        """
        Analyze a test result and detect contamination issues.

        Args:
            test_result: TestResult object with water quality parameters

        Returns:
            Dict with detected issues and recommended contamination types
        """
        issues = []
        contamination_types = set()

        for field, threshold in self.THRESHOLDS.items():
            value = getattr(test_result, field, None)
            if value is None:
                continue

            issue = None
            if 'min' in threshold and value < threshold['min']:
                issue = {
                    'parameter': threshold['param'],
                    'value': value,
                    'threshold': f"min {threshold['min']}",
                    'severity': 'high' if abs(value - threshold['min']) > threshold['min'] * 0.2 else 'medium'
                }
            elif 'max' in threshold and value > threshold['max']:
                issue = {
                    'parameter': threshold['param'],
                    'value': value,
                    'threshold': f"max {threshold['max']}",
                    'severity': 'high' if value > threshold['max'] * 1.5 else 'medium'
                }

            if issue:
                issue['contamination_type'] = threshold['type']
                issues.append(issue)
                contamination_types.add(threshold['type'])

        return {
            'has_contamination': len(issues) > 0,
            'issues': issues,
            'contamination_types': list(contamination_types),
            'severity': 'high' if any(i['severity'] == 'high' for i in issues) else 'medium' if issues else 'none'
        }

    def suggest_interventions_for_sample(self, sample_id):
        """
        Analyze a water sample and suggest interventions if contamination detected.

        Args:
            sample_id: ID of the WaterSample to analyze

        Returns:
            Dict with contamination analysis and suggested interventions
        """
        from app.models.test_result import TestResult

        test_result = TestResult.query.filter_by(sample_id=sample_id).first()
        if not test_result:
            return {'error': 'No test results found for sample'}

        # Detect contamination
        contamination = self.detect_contamination_from_test(test_result)

        if not contamination['has_contamination']:
            return {
                'sample_id': sample_id,
                'needs_intervention': False,
                'message': 'Water quality within acceptable limits'
            }

        # Get treatment recommendations for each contamination type
        all_recommendations = []
        for cont_type in contamination['contamination_types']:
            recs = self.recommend_treatment(cont_type)
            if recs.get('recommendations'):
                all_recommendations.extend(recs['recommendations'][:2])  # Top 2 per type

        return {
            'sample_id': sample_id,
            'needs_intervention': True,
            'contamination': contamination,
            'suggested_treatments': all_recommendations[:5],  # Top 5 overall
            'message': f"Detected {len(contamination['issues'])} water quality issues requiring intervention"
        }

    def create_planned_intervention(self, site_id, sample_id, treatment_method_id, parameter, before_value, admin_user_id=None):
        """
        Create a planned intervention record from detected contamination.

        Args:
            site_id: Site where intervention is needed
            sample_id: Sample that triggered the intervention
            treatment_method_id: ID of selected treatment method
            parameter: Parameter to target (ph, turbidity, etc.)
            before_value: Current value of the parameter
            admin_user_id: User creating the intervention

        Returns:
            Created Intervention object or error dict
        """
        from datetime import date

        method = TreatmentMethod.query.get(treatment_method_id)
        if not method:
            return {'error': 'Treatment method not found'}

        intervention = Intervention(
            site_id=site_id,
            treatment_method_id=treatment_method_id,
            intervention_type='treatment',
            intervention_date=date.today(),
            description=f"Auto-suggested: {method.method_name} for {parameter} (value: {before_value})",
            parameter_targeted=parameter,
            before_value=before_value,
            status='planned',
            created_by=admin_user_id
        )

        db.session.add(intervention)
        db.session.commit()

        return intervention
