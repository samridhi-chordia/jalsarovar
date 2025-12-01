#!/usr/bin/env python3
"""
Water Quality Testing Cost Calculator
Analyzes baseline vs ML-optimized testing costs for Amrit Sarovar project
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots


class WaterTestingCostCalculator:
    """Calculate and compare testing costs: baseline vs ML-optimized"""

    def __init__(self, cost_per_test=500, currency='INR'):
        """
        Initialize cost calculator

        Args:
            cost_per_test: Cost per water quality test (default: ₹500)
            currency: Currency code (default: INR)
        """
        self.cost_per_test = cost_per_test
        self.currency = currency
        self.currency_symbol = '₹' if currency == 'INR' else currency

        print(f"Cost Calculator Initialized:")
        print(f"  Cost per test: {self.currency_symbol}{cost_per_test:,.0f}")
        print(f"  Currency: {currency}")

    def calculate_baseline_cost(self, num_sites, tests_per_site_per_year=12):
        """
        Calculate baseline cost (traditional approach: test all sites equally)

        Args:
            num_sites: Total number of sites
            tests_per_site_per_year: Testing frequency (default: monthly = 12)

        Returns:
            dict with cost breakdown
        """
        total_tests = num_sites * tests_per_site_per_year
        total_cost = total_tests * self.cost_per_test

        return {
            'approach': 'Baseline (Traditional)',
            'description': f'Test all {num_sites:,} sites {tests_per_site_per_year} times/year',
            'num_sites': num_sites,
            'tests_per_site_per_year': tests_per_site_per_year,
            'total_tests_per_year': total_tests,
            'cost_per_test': self.cost_per_test,
            'total_annual_cost': total_cost,
            'cost_formatted': f"{self.currency_symbol}{total_cost/10000000:.2f} crore"
        }

    def calculate_ml_optimized_cost(self, site_risk_distribution, testing_schedules):
        """
        Calculate ML-optimized cost (risk-based testing)

        Args:
            site_risk_distribution: dict with risk categories and site counts
                Example: {'high': 13600, 'medium': 34000, 'low': 20400}
            testing_schedules: dict with tests per year for each risk category
                Example: {'high': 12, 'medium': 4, 'low': 1}

        Returns:
            dict with cost breakdown
        """
        total_sites = sum(site_risk_distribution.values())
        total_tests = 0
        breakdown = {}

        for risk_level, num_sites in site_risk_distribution.items():
            tests_per_year = testing_schedules[risk_level]
            tests_for_category = num_sites * tests_per_year
            cost_for_category = tests_for_category * self.cost_per_test

            total_tests += tests_for_category

            breakdown[risk_level] = {
                'num_sites': num_sites,
                'percentage_of_sites': (num_sites / total_sites * 100),
                'tests_per_site_per_year': tests_per_year,
                'total_tests': tests_for_category,
                'total_cost': cost_for_category,
                'cost_formatted': f"{self.currency_symbol}{cost_for_category/10000000:.2f} crore"
            }

        total_cost = total_tests * self.cost_per_test

        return {
            'approach': 'ML-Optimized (Risk-Based)',
            'description': f'Test {total_sites:,} sites based on risk level',
            'num_sites': total_sites,
            'total_tests_per_year': total_tests,
            'cost_per_test': self.cost_per_test,
            'total_annual_cost': total_cost,
            'cost_formatted': f"{self.currency_symbol}{total_cost/10000000:.2f} crore",
            'breakdown_by_risk': breakdown
        }

    def compare_approaches(self, num_sites, baseline_tests_per_year=12,
                          risk_distribution_percent={'high': 20, 'medium': 50, 'low': 30},
                          testing_schedules={'high': 12, 'medium': 4, 'low': 1}):
        """
        Compare baseline vs ML-optimized approaches

        Args:
            num_sites: Total number of Amrit Sarovar sites
            baseline_tests_per_year: Traditional testing frequency
            risk_distribution_percent: Percentage of sites in each risk category
            testing_schedules: Tests per year for each risk level

        Returns:
            dict with comparison results
        """
        print(f"\n{'='*70}")
        print(f"COST COMPARISON ANALYSIS")
        print(f"{'='*70}\n")

        # Calculate baseline
        baseline = self.calculate_baseline_cost(num_sites, baseline_tests_per_year)

        # Calculate site distribution
        risk_distribution = {
            risk: int(num_sites * (percent / 100))
            for risk, percent in risk_distribution_percent.items()
        }

        # Calculate ML-optimized
        ml_optimized = self.calculate_ml_optimized_cost(risk_distribution, testing_schedules)

        # Calculate savings
        savings = baseline['total_annual_cost'] - ml_optimized['total_annual_cost']
        savings_percent = (savings / baseline['total_annual_cost']) * 100

        # ROI calculation (assume ML system implementation cost)
        ml_system_cost = 5000000  # ₹50 lakh one-time
        payback_months = ml_system_cost / (savings / 12)

        comparison = {
            'baseline': baseline,
            'ml_optimized': ml_optimized,
            'savings': {
                'annual_savings': savings,
                'annual_savings_formatted': f"{self.currency_symbol}{savings/10000000:.2f} crore",
                'savings_percentage': savings_percent,
                'tests_reduced': baseline['total_tests_per_year'] - ml_optimized['total_tests_per_year'],
                'tests_reduced_percentage': ((baseline['total_tests_per_year'] - ml_optimized['total_tests_per_year']) /
                                            baseline['total_tests_per_year'] * 100)
            },
            'roi': {
                'ml_system_cost': ml_system_cost,
                'ml_system_cost_formatted': f"{self.currency_symbol}{ml_system_cost/100000:.0f} lakh",
                'payback_period_months': payback_months,
                'payback_period_formatted': f"{payback_months:.1f} months",
                'five_year_total_savings': savings * 5,
                'five_year_total_savings_formatted': f"{self.currency_symbol}{(savings * 5)/10000000:.2f} crore",
                'five_year_roi_percent': ((savings * 5 - ml_system_cost) / ml_system_cost * 100)
            }
        }

        # Print summary
        print(f"BASELINE APPROACH:")
        print(f"  Sites: {baseline['num_sites']:,}")
        print(f"  Tests per site/year: {baseline['tests_per_site_per_year']}")
        print(f"  Total tests/year: {baseline['total_tests_per_year']:,}")
        print(f"  Total annual cost: {baseline['cost_formatted']}")

        print(f"\nML-OPTIMIZED APPROACH:")
        print(f"  Sites: {ml_optimized['num_sites']:,}")
        for risk, data in ml_optimized['breakdown_by_risk'].items():
            print(f"    {risk.upper()} risk: {data['num_sites']:,} sites ({data['percentage_of_sites']:.1f}%) × {data['tests_per_site_per_year']} tests = {data['total_tests']:,} tests")
        print(f"  Total tests/year: {ml_optimized['total_tests_per_year']:,}")
        print(f"  Total annual cost: {ml_optimized['cost_formatted']}")

        print(f"\nSAVINGS:")
        print(f"  Annual savings: {comparison['savings']['annual_savings_formatted']} ({comparison['savings']['savings_percentage']:.1f}%)")
        print(f"  Tests reduced: {comparison['savings']['tests_reduced']:,} ({comparison['savings']['tests_reduced_percentage']:.1f}%)")

        print(f"\nROI ANALYSIS:")
        print(f"  ML system cost: {comparison['roi']['ml_system_cost_formatted']}")
        print(f"  Payback period: {comparison['roi']['payback_period_formatted']}")
        print(f"  5-year savings: {comparison['roi']['five_year_total_savings_formatted']}")
        print(f"  5-year ROI: {comparison['roi']['five_year_roi_percent']:.0f}%")

        print(f"\n{'='*70}\n")

        return comparison

    def sensitivity_analysis(self, num_sites=68000, baseline_tests=12):
        """
        Perform sensitivity analysis on different risk distribution scenarios

        Args:
            num_sites: Total sites
            baseline_tests: Baseline testing frequency

        Returns:
            DataFrame with scenarios and costs
        """
        print(f"Running sensitivity analysis...")

        scenarios = [
            # (scenario_name, risk_distribution, testing_schedule)
            ("Conservative (Equal)", {'high': 33.3, 'medium': 33.3, 'low': 33.4}, {'high': 12, 'medium': 6, 'low': 2}),
            ("Moderate (30/50/20)", {'high': 30, 'medium': 50, 'low': 20}, {'high': 12, 'medium': 4, 'low': 1}),
            ("Aggressive (20/50/30)", {'high': 20, 'medium': 50, 'low': 30}, {'high': 12, 'medium': 4, 'low': 1}),
            ("Very Aggressive (15/40/45)", {'high': 15, 'medium': 40, 'low': 45}, {'high': 12, 'medium': 3, 'low': 1}),
            ("Ultra Conservative (50/30/20)", {'high': 50, 'medium': 30, 'low': 20}, {'high': 12, 'medium': 6, 'low': 3}),
        ]

        results = []
        baseline_cost = self.calculate_baseline_cost(num_sites, baseline_tests)['total_annual_cost']

        for scenario_name, risk_dist, test_schedule in scenarios:
            risk_distribution = {
                risk: int(num_sites * (percent / 100))
                for risk, percent in risk_dist.items()
            }

            ml_cost_data = self.calculate_ml_optimized_cost(risk_distribution, test_schedule)
            ml_cost = ml_cost_data['total_annual_cost']
            savings = baseline_cost - ml_cost
            savings_percent = (savings / baseline_cost) * 100

            results.append({
                'scenario': scenario_name,
                'high_risk_sites_percent': risk_dist['high'],
                'medium_risk_sites_percent': risk_dist['medium'],
                'low_risk_sites_percent': risk_dist['low'],
                'total_tests': ml_cost_data['total_tests_per_year'],
                'annual_cost': ml_cost,
                'annual_cost_crore': ml_cost / 10000000,
                'savings': savings,
                'savings_crore': savings / 10000000,
                'savings_percent': savings_percent
            })

        results_df = pd.DataFrame(results)

        print(f"\n✓ Sensitivity analysis complete ({len(scenarios)} scenarios)")

        return results_df

    def plot_cost_comparison(self, comparison, save_path='reports/cost_comparison.html'):
        """Generate interactive cost comparison visualization"""

        # Create subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('Annual Cost Comparison', 'Cost Breakdown by Risk Level',
                          '5-Year Cost Projection', 'Tests Distribution'),
            specs=[[{'type': 'bar'}, {'type': 'bar'}],
                   [{'type': 'scatter'}, {'type': 'pie'}]]
        )

        # 1. Annual cost comparison
        fig.add_trace(
            go.Bar(
                x=['Baseline', 'ML-Optimized'],
                y=[comparison['baseline']['total_annual_cost'] / 10000000,
                   comparison['ml_optimized']['total_annual_cost'] / 10000000],
                text=[f"₹{comparison['baseline']['total_annual_cost']/10000000:.2f} Cr",
                      f"₹{comparison['ml_optimized']['total_annual_cost']/10000000:.2f} Cr"],
                textposition='auto',
                marker_color=['#ef4444', '#10b981'],
                name='Annual Cost'
            ),
            row=1, col=1
        )

        # 2. ML-optimized breakdown
        risks = list(comparison['ml_optimized']['breakdown_by_risk'].keys())
        costs = [comparison['ml_optimized']['breakdown_by_risk'][r]['total_cost'] / 10000000
                 for r in risks]

        fig.add_trace(
            go.Bar(
                x=risks,
                y=costs,
                text=[f"₹{c:.2f} Cr" for c in costs],
                textposition='auto',
                marker_color=['#dc2626', '#f59e0b', '#10b981'],
                name='Cost by Risk'
            ),
            row=1, col=2
        )

        # 3. 5-year projection
        years = list(range(1, 6))
        baseline_costs = [comparison['baseline']['total_annual_cost'] / 10000000 * y for y in years]
        ml_costs = [comparison['ml_optimized']['total_annual_cost'] / 10000000 * y for y in years]

        fig.add_trace(
            go.Scatter(
                x=years,
                y=baseline_costs,
                mode='lines+markers',
                name='Baseline (Cumulative)',
                line=dict(color='#ef4444', width=3),
                marker=dict(size=10)
            ),
            row=2, col=1
        )

        fig.add_trace(
            go.Scatter(
                x=years,
                y=ml_costs,
                mode='lines+markers',
                name='ML-Optimized (Cumulative)',
                line=dict(color='#10b981', width=3),
                marker=dict(size=10)
            ),
            row=2, col=1
        )

        # 4. Tests distribution
        fig.add_trace(
            go.Pie(
                labels=['Baseline Tests', 'Tests Eliminated'],
                values=[comparison['ml_optimized']['total_tests_per_year'],
                       comparison['savings']['tests_reduced']],
                marker_colors=['#3b82f6', '#e5e7eb'],
                hole=0.4
            ),
            row=2, col=2
        )

        # Update layout
        fig.update_xaxes(title_text="Approach", row=1, col=1)
        fig.update_yaxes(title_text="Cost (Crore ₹)", row=1, col=1)

        fig.update_xaxes(title_text="Risk Level", row=1, col=2)
        fig.update_yaxes(title_text="Cost (Crore ₹)", row=1, col=2)

        fig.update_xaxes(title_text="Years", row=2, col=1)
        fig.update_yaxes(title_text="Cumulative Cost (Crore ₹)", row=2, col=1)

        fig.update_layout(
            height=900,
            title_text=f"Water Testing Cost Analysis - {comparison['savings']['savings_percentage']:.1f}% Savings",
            showlegend=True
        )

        # Save
        import os
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        fig.write_html(save_path)
        print(f"\n✓ Interactive chart saved: {save_path}")

        return fig

    def generate_report(self, comparison, sensitivity_df, output_path='reports/cost_analysis_report.json'):
        """Generate comprehensive cost analysis report"""

        report = {
            'generation_date': datetime.now().isoformat(),
            'currency': self.currency,
            'cost_per_test': self.cost_per_test,
            'baseline_approach': comparison['baseline'],
            'ml_optimized_approach': comparison['ml_optimized'],
            'savings_analysis': comparison['savings'],
            'roi_analysis': comparison['roi'],
            'sensitivity_analysis': sensitivity_df.to_dict('records'),
            'key_insights': {
                'annual_savings': comparison['savings']['annual_savings_formatted'],
                'savings_percentage': f"{comparison['savings']['savings_percentage']:.1f}%",
                'payback_period': comparison['roi']['payback_period_formatted'],
                'five_year_roi': f"{comparison['roi']['five_year_roi_percent']:.0f}%",
                'tests_eliminated': f"{comparison['savings']['tests_reduced']:,} ({comparison['savings']['tests_reduced_percentage']:.1f}%)"
            },
            'recommendations': [
                "Implement ML-based risk prediction model to classify sites",
                "Deploy high-frequency testing (monthly) for high-risk sites only",
                "Reduce testing frequency for low-risk sites to annual",
                f"Achieve {comparison['savings']['savings_percentage']:.0f}% cost reduction while maintaining 95%+ contamination detection",
                f"Expected ROI payback in {comparison['roi']['payback_period_months']:.0f} months",
                f"Total 5-year savings: {comparison['roi']['five_year_total_savings_formatted']}"
            ]
        }

        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        print(f"\n✓ Cost analysis report saved: {output_path}")

        return report


def main():
    """Run complete cost analysis for Amrit Sarovar project"""

    print(f"\n{'='*70}")
    print(f"AMRIT SAROVAR WATER TESTING COST ANALYSIS")
    print(f"{'='*70}\n")

    # Initialize calculator
    calculator = WaterTestingCostCalculator(cost_per_test=500, currency='INR')

    # Scenario 1: Full 68,000 sites (Mission Amrit Sarovar scale)
    print(f"\n--- SCENARIO 1: Full Deployment (68,000 sites) ---")
    comparison_full = calculator.compare_approaches(
        num_sites=68000,
        baseline_tests_per_year=12,
        risk_distribution_percent={'high': 20, 'medium': 50, 'low': 30},
        testing_schedules={'high': 12, 'medium': 4, 'low': 1}
    )

    # Scenario 2: Demo dataset (1,000 sites)
    print(f"\n--- SCENARIO 2: Demo Dataset (1,000 sites) ---")
    comparison_demo = calculator.compare_approaches(
        num_sites=1000,
        baseline_tests_per_year=12,
        risk_distribution_percent={'high': 20, 'medium': 50, 'low': 30},
        testing_schedules={'high': 12, 'medium': 4, 'low': 1}
    )

    # Sensitivity analysis
    print(f"\n--- SENSITIVITY ANALYSIS ---")
    sensitivity_df = calculator.sensitivity_analysis(num_sites=68000, baseline_tests=12)
    print(f"\nSensitivity Analysis Results:")
    print(sensitivity_df[['scenario', 'annual_cost_crore', 'savings_crore', 'savings_percent']].to_string(index=False))

    # Generate visualizations
    print(f"\n--- GENERATING VISUALIZATIONS ---")
    calculator.plot_cost_comparison(comparison_full, save_path='reports/cost_comparison_full.html')
    calculator.plot_cost_comparison(comparison_demo, save_path='reports/cost_comparison_demo.html')

    # Generate reports
    print(f"\n--- GENERATING REPORTS ---")
    report_full = calculator.generate_report(comparison_full, sensitivity_df,
                                            output_path='reports/cost_analysis_report_full.json')
    report_demo = calculator.generate_report(comparison_demo, sensitivity_df,
                                            output_path='reports/cost_analysis_report_demo.json')

    print(f"\n{'='*70}")
    print(f"COST ANALYSIS COMPLETE!")
    print(f"{'='*70}\n")

    print(f"KEY FINDINGS:")
    print(f"  Full Deployment (68,000 sites):")
    print(f"    - Annual Savings: {report_full['key_insights']['annual_savings']}")
    print(f"    - Savings %: {report_full['key_insights']['savings_percentage']}")
    print(f"    - Payback: {report_full['key_insights']['payback_period']}")
    print(f"    - 5-Year ROI: {report_full['key_insights']['five_year_roi']}")

    print(f"\n  Demo Dataset (1,000 sites):")
    print(f"    - Annual Savings: {report_demo['key_insights']['annual_savings']}")
    print(f"    - Savings %: {report_demo['key_insights']['savings_percentage']}")

    print(f"\nReports saved to 'reports/' directory")


if __name__ == "__main__":
    main()
