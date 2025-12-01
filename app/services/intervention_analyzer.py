"""
Intervention Analyzer Service
Analyzes effectiveness of water treatment interventions
"""
from app.models.intervention import Intervention
from app.models.treatment_method import TreatmentMethod
from app.models.water_sample import WaterSample
from app.models.test_result import TestResult
from app import db
from sqlalchemy import func, and_, or_


class InterventionAnalyzer:
    """
    Service for analyzing intervention effectiveness and providing recommendations.

    Features:
    - Pre/post quality comparison
    - Statistical significance testing
    - ROI calculation
    - Treatment recommendations by contamination type
    """

    def __init__(self):
        pass

    def analyze_intervention(self, intervention_id):
        """
        Comprehensive analysis of a single intervention's effectiveness.

        Returns dict with:
        - pre_post_comparison
        - improvement_metrics
        - cost_effectiveness
        - recommendations
        """
        intervention = Intervention.query.get(intervention_id)
        if not intervention:
            return {'error': 'Intervention not found'}

        if not intervention.sample or not intervention.followup_sample:
            return {'error': 'Missing baseline or followup sample data'}

        analysis = {
            'intervention': intervention.to_dict(),
            'pre_post_comparison': self._compare_samples(
                intervention.sample,
                intervention.followup_sample
            ),
            'improvement_metrics': {},
            'cost_effectiveness': {},
            'recommendations': []
        }

        # Calculate overall improvement
        comparison = analysis['pre_post_comparison']
        improvements = [param['improvement_pct'] for param in comparison['parameters'].values()
                       if param['improvement_pct'] is not None]

        if improvements:
            avg_improvement = sum(improvements) / len(improvements)
            analysis['improvement_metrics']['average_improvement'] = round(avg_improvement, 2)
            analysis['improvement_metrics']['best_improvement'] = round(max(improvements), 2)
            analysis['improvement_metrics']['worst_improvement'] = round(min(improvements), 2)

            # Determine effectiveness
            if avg_improvement > 30:
                analysis['improvement_metrics']['effectiveness'] = 'Highly Effective'
            elif avg_improvement > 10:
                analysis['improvement_metrics']['effectiveness'] = 'Moderately Effective'
            elif avg_improvement > 0:
                analysis['improvement_metrics']['effectiveness'] = 'Marginally Effective'
            else:
                analysis['improvement_metrics']['effectiveness'] = 'Not Effective'

        # Cost effectiveness (improvement per unit cost)
        if intervention.cost and improvements:
            cost_per_percent_improvement = intervention.cost / max(avg_improvement, 1)
            analysis['cost_effectiveness'] = {
                'cost': intervention.cost,
                'cost_currency': intervention.cost_currency,
                'cost_per_percent_improvement': round(cost_per_percent_improvement, 2),
                'value_rating': self._rate_cost_effectiveness(cost_per_percent_improvement)
            }

        # Recommendations
        if avg_improvement < 20:
            analysis['recommendations'].append(
                "Consider additional or alternative treatment methods"
            )

        if intervention.duration_days and intervention.duration_days > 90:
            analysis['recommendations'].append(
                "Implementation took longer than typical - review process efficiency"
            )

        return analysis

    def _compare_samples(self, baseline_sample, followup_sample):
        """
        Compare water quality between baseline and followup samples.

        Returns detailed parameter-by-parameter comparison.
        """
        # Get test results for both samples
        baseline_tests = {
            tr.parameter_name: tr.value
            for tr in baseline_sample.test_results
        }

        followup_tests = {
            tr.parameter_name: tr.value
            for tr in followup_sample.test_results
        }

        comparison = {
            'baseline_sample_id': baseline_sample.sample_id,
            'followup_sample_id': followup_sample.sample_id,
            'baseline_date': baseline_sample.collection_date.isoformat() if baseline_sample.collection_date else None,
            'followup_date': followup_sample.collection_date.isoformat() if followup_sample.collection_date else None,
            'parameters': {}
        }

        # Compare each parameter
        for param, baseline_value in baseline_tests.items():
            if param in followup_tests:
                followup_value = followup_tests[param]

                # Calculate change
                absolute_change = baseline_value - followup_value

                # For most contaminants, lower is better (positive change is improvement)
                # For pH and DO, closer to ideal is better (handled separately)
                improvement_pct = None
                if baseline_value > 0:
                    improvement_pct = (absolute_change / baseline_value) * 100

                comparison['parameters'][param] = {
                    'baseline': baseline_value,
                    'followup': followup_value,
                    'absolute_change': round(absolute_change, 4),
                    'improvement_pct': round(improvement_pct, 2) if improvement_pct is not None else None,
                    'direction': 'improved' if absolute_change > 0 else 'worsened' if absolute_change < 0 else 'unchanged'
                }

        return comparison

    def _rate_cost_effectiveness(self, cost_per_percent):
        """Rate cost effectiveness on a simple scale"""
        if cost_per_percent < 100:
            return 'Excellent'
        elif cost_per_percent < 500:
            return 'Good'
        elif cost_per_percent < 1000:
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
                    'treatment_method': method.name,
                    'category': method.category,
                    'total_interventions': 0,
                    'successful_interventions': 0,
                    'success_rate': 0,
                    'average_improvement': None,
                    'average_cost': None
                })
                continue

            # Count successful ones
            successful = sum(1 for i in completed if i.was_successful())

            # Calculate averages
            improvements = [i.improvement_percentage for i in completed if i.improvement_percentage is not None]
            avg_improvement = sum(improvements) / len(improvements) if improvements else None

            costs = [i.cost for i in completed if i.cost is not None]
            avg_cost = sum(costs) / len(costs) if costs else None

            success_rate = (successful / len(completed)) * 100

            results.append({
                'treatment_method': method.name,
                'category': method.category,
                'total_interventions': len(completed),
                'successful_interventions': successful,
                'success_rate': round(success_rate, 1),
                'average_improvement': round(avg_improvement, 2) if avg_improvement else None,
                'average_cost': round(avg_cost, 2) if avg_cost else None,
                'cost_currency': method.cost_currency
            })

        # Sort by success rate descending
        results.sort(key=lambda x: x['success_rate'], reverse=True)

        return results

    def recommend_treatment(self, contamination_type, budget=None):
        """
        Recommend most effective treatment methods for a specific contamination type.

        Args:
            contamination_type: String like 'arsenic', 'lead', 'bacterial', etc.
            budget: Optional maximum budget constraint

        Returns:
            List of recommended treatment methods sorted by effectiveness
        """
        # Get treatment methods that are suitable for this contamination type
        methods = TreatmentMethod.query.filter_by(is_active=True).all()

        suitable_methods = []
        for method in methods:
            contaminants = method.get_suitable_contaminants()
            if contamination_type.lower() in [c.lower() for c in contaminants]:
                suitable_methods.append(method)

        if not suitable_methods:
            return {
                'contamination_type': contamination_type,
                'recommendations': [],
                'message': f'No treatment methods found for {contamination_type}'
            }

        recommendations = []
        for method in suitable_methods:
            # Skip if over budget
            if budget and method.typical_cost_min and method.typical_cost_min > budget:
                continue

            # Get historical effectiveness
            effectiveness_data = self._get_method_effectiveness(method.id, contamination_type)

            rec = {
                'treatment_method': method.name,
                'category': method.category,
                'description': method.description,
                'cost_range': method.cost_range_display,
                'implementation_days': method.implementation_time_days,
                'technical_complexity': method.technical_complexity,
                'effectiveness_rate': method.effectiveness_rate or effectiveness_data['effectiveness_rate'],
                'historical_uses': effectiveness_data['intervention_count'],
                'average_improvement': effectiveness_data['average_improvement']
            }

            recommendations.append(rec)

        # Sort by effectiveness rate
        recommendations.sort(
            key=lambda x: (x['effectiveness_rate'] or 0, x['historical_uses'] or 0),
            reverse=True
        )

        return {
            'contamination_type': contamination_type,
            'budget': budget,
            'recommendations': recommendations
        }

    def _get_method_effectiveness(self, treatment_method_id, contamination_type=None):
        """Get effectiveness metrics for a specific treatment method"""
        query = Intervention.query.filter_by(
            treatment_method_id=treatment_method_id,
            status='completed'
        )

        interventions = query.all()

        if not interventions:
            return {
                'effectiveness_rate': 0,
                'intervention_count': 0,
                'average_improvement': None
            }

        successful = sum(1 for i in interventions if i.was_successful())
        improvements = [i.improvement_percentage for i in interventions if i.improvement_percentage]

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

        # Get successful interventions
        successful_interventions = Intervention.query.filter(
            Intervention.status == 'completed',
            Intervention.was_effective == True
        ).count()

        # Calculate average metrics for completed interventions
        completed_list = Intervention.query.filter_by(status='completed').all()

        avg_improvement = None
        avg_cost = None
        total_cost = 0

        if completed_list:
            improvements = [i.improvement_percentage for i in completed_list if i.improvement_percentage]
            if improvements:
                avg_improvement = sum(improvements) / len(improvements)

            costs = [i.cost for i in completed_list if i.cost]
            if costs:
                avg_cost = sum(costs) / len(costs)
                total_cost = sum(costs)

        return {
            'total_interventions': total,
            'by_status': {
                'planned': planned,
                'in_progress': in_progress,
                'completed': completed
            },
            'successful_interventions': successful_interventions,
            'success_rate': round((successful_interventions / completed) * 100, 1) if completed > 0 else 0,
            'average_improvement': round(avg_improvement, 2) if avg_improvement else None,
            'average_cost': round(avg_cost, 2) if avg_cost else None,
            'total_cost': round(total_cost, 2) if total_cost else 0
        }

    def calculate_roi(self, intervention_id):
        """
        Calculate Return on Investment for an intervention.

        ROI = (Quality Improvement Value - Cost) / Cost * 100

        Note: This is a simplified calculation. In reality, you'd need to assign
        monetary value to water quality improvements.
        """
        intervention = Intervention.query.get(intervention_id)
        if not intervention or intervention.status != 'completed':
            return None

        if not intervention.cost or not intervention.improvement_percentage:
            return None

        # Simplified: assume each 1% improvement is worth $100
        # In practice, this should be based on health impact, DALY analysis, etc.
        improvement_value = intervention.improvement_percentage * 100

        roi = ((improvement_value - intervention.cost) / intervention.cost) * 100

        return {
            'intervention_id': intervention_id,
            'cost': intervention.cost,
            'improvement_percentage': intervention.improvement_percentage,
            'estimated_value': improvement_value,
            'roi_percentage': round(roi, 2),
            'note': 'This is a simplified calculation. Actual ROI should consider health outcomes and long-term benefits.'
        }
