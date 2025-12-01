#!/usr/bin/env python3
"""
Synthetic Water Quality Data Generator for Amrit Sarovar Demo
Generates realistic water quality samples based on Indian water standards (BIS/WHO)
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import json

class AmritSarovarDataGenerator:
    """Generate realistic synthetic water quality data for demo/POC"""

    # Indian states with Amrit Sarovar projects (Phase 1)
    STATES = [
        'Uttar Pradesh', 'Madhya Pradesh', 'Tamil Nadu', 'Karnataka', 'Maharashtra',
        'Rajasthan', 'Gujarat', 'Andhra Pradesh', 'Telangana', 'Bihar',
        'Odisha', 'West Bengal', 'Punjab', 'Haryana', 'Jharkhand'
    ]

    # Water body types
    WATER_BODY_TYPES = ['Pond', 'Lake', 'Tank', 'Reservoir', 'Step Well']

    # Environment types
    ENVIRONMENT_TYPES = ['Rural Agricultural', 'Rural', 'Semi-Urban', 'Urban', 'Industrial']

    # Contamination sources
    CONTAMINATION_SOURCES = [
        'runoff_sediment', 'sewage_ingress', 'salt_intrusion',
        'pipe_corrosion', 'disinfectant_decay', 'agricultural', 'industrial'
    ]

    def __init__(self, num_sites=1000, samples_per_site=12, seed=42):
        """
        Initialize generator

        Args:
            num_sites: Number of Amrit Sarovar sites to generate
            samples_per_site: Number of water samples per site (monthly over 1 year)
            seed: Random seed for reproducibility
        """
        self.num_sites = num_sites
        self.samples_per_site = samples_per_site
        self.seed = seed
        np.random.seed(seed)
        random.seed(seed)

        print(f"Initialized Amrit Sarovar Data Generator:")
        print(f"  - Sites: {num_sites}")
        print(f"  - Samples per site: {samples_per_site}")
        print(f"  - Total samples: {num_sites * samples_per_site:,}")

    def generate_sites(self):
        """Generate synthetic Amrit Sarovar site data"""
        sites = []

        for i in range(self.num_sites):
            state = random.choice(self.STATES)
            site_code = f"AS-{state[:2].upper()}-{i+1:04d}"

            # Assign environment type (weighted towards rural)
            env_weights = [0.4, 0.25, 0.2, 0.1, 0.05]  # More rural sites
            environment_type = np.random.choice(self.ENVIRONMENT_TYPES, p=env_weights)

            # Generate GPS coordinates (India bounds: 8-35°N, 68-98°E)
            latitude = np.random.uniform(8.0, 35.0)
            longitude = np.random.uniform(68.0, 98.0)

            # Industrial/agricultural proximity (affects contamination)
            industrial_nearby = (environment_type in ['Industrial', 'Semi-Urban', 'Urban']) or (np.random.random() < 0.15)
            agricultural_nearby = (environment_type == 'Rural Agricultural') or (np.random.random() < 0.6)

            # Population density (people per sq km)
            if environment_type == 'Rural':
                pop_density = np.random.lognormal(5, 0.5)  # ~150-300
            elif environment_type == 'Rural Agricultural':
                pop_density = np.random.lognormal(5.5, 0.5)  # ~200-400
            elif environment_type == 'Semi-Urban':
                pop_density = np.random.lognormal(7, 0.5)  # ~1,000-2,000
            elif environment_type == 'Urban':
                pop_density = np.random.lognormal(8.5, 0.5)  # ~5,000-10,000
            else:  # Industrial
                pop_density = np.random.lognormal(8, 0.7)  # ~3,000-8,000

            site = {
                'site_code': site_code,
                'site_name': f"Amrit Sarovar {site_code}",
                'state': state,
                'district': f"{state} District {np.random.randint(1, 30)}",
                'latitude': round(latitude, 6),
                'longitude': round(longitude, 6),
                'environment_type': environment_type,
                'water_body_type': random.choice(self.WATER_BODY_TYPES),
                'is_coastal': np.random.random() < 0.05,  # 5% coastal
                'industrial_nearby': industrial_nearby,
                'agricultural_nearby': agricultural_nearby,
                'population_density': int(pop_density),
                'is_active': True,
                'created_at': datetime.now() - timedelta(days=random.randint(365, 730))
            }

            sites.append(site)

        print(f"\n✓ Generated {len(sites)} sites")
        return pd.DataFrame(sites)

    def _generate_water_quality_params(self, site_data, month_offset, historical_contamination):
        """Generate realistic water quality parameters based on site characteristics"""

        # Base parameters (clean water)
        params = {
            'ph': 7.0,
            'temperature': 25.0,
            'turbidity': 2.0,
            'tds': 150.0,
            'conductivity': 300.0,
            'total_hardness': 100.0,
            'chlorine_residual': 0.5,
            'dissolved_oxygen': 7.0,
            'bod': 2.0,
            'cod': 10.0,
            'nitrate': 5.0,
            'fluoride': 0.5,
            'iron': 0.1,
            'arsenic': 0.005,
            'lead': 0.005,
            'coliform_status': 'absent'
        }

        # Seasonal variation (month 0-11)
        current_month = month_offset % 12
        is_monsoon = current_month in [5, 6, 7, 8]  # June-Sep
        is_summer = current_month in [3, 4, 5]  # Apr-Jun
        is_winter = current_month in [11, 0, 1]  # Dec-Feb

        # Temperature variation
        if is_summer:
            params['temperature'] += np.random.uniform(5, 10)
        elif is_winter:
            params['temperature'] -= np.random.uniform(3, 8)
        elif is_monsoon:
            params['temperature'] += np.random.uniform(-2, 3)

        # Add site-specific contamination
        env_type = site_data['environment_type']

        # 1. Agricultural runoff
        if site_data['agricultural_nearby'] or env_type == 'Rural Agricultural':
            contamination_level = np.random.uniform(0.2, 0.8)
            if is_monsoon:  # Worse during monsoon
                contamination_level *= 1.5

            params['turbidity'] += contamination_level * 20
            params['nitrate'] += contamination_level * 30
            params['tds'] += contamination_level * 150
            params['conductivity'] += contamination_level * 300
            params['ph'] += np.random.uniform(-0.5, 0.3)

            if contamination_level > 0.5:
                params['coliform_status'] = 'present'

        # 2. Sewage contamination
        if env_type in ['Urban', 'Semi-Urban']:
            sewage_level = np.random.uniform(0.1, 0.7)

            params['bod'] += sewage_level * 25
            params['cod'] += sewage_level * 60
            params['nitrate'] += sewage_level * 25
            params['turbidity'] += sewage_level * 30
            params['tds'] += sewage_level * 200
            params['ph'] -= sewage_level * 0.5

            if sewage_level > 0.4:
                params['coliform_status'] = 'present'

        # 3. Industrial contamination
        if site_data['industrial_nearby'] or env_type == 'Industrial':
            industrial_level = np.random.uniform(0.15, 0.9)

            params['tds'] += industrial_level * 300
            params['conductivity'] += industrial_level * 600
            params['iron'] += industrial_level * 1.5
            params['lead'] += industrial_level * 0.03
            params['arsenic'] += industrial_level * 0.02
            params['ph'] += np.random.uniform(-1.0, 1.5)
            params['turbidity'] += industrial_level * 15

        # 4. Salt intrusion (coastal areas)
        if site_data['is_coastal']:
            salt_level = np.random.uniform(0.2, 0.9)
            params['tds'] += salt_level * 500
            params['conductivity'] += salt_level * 1000
            params['chlorine_residual'] += salt_level * 2

        # 5. Pipe corrosion (older infrastructure)
        if env_type in ['Urban', 'Semi-Urban']:
            corrosion_level = np.random.uniform(0.1, 0.6)
            params['iron'] += corrosion_level * 0.8
            params['lead'] += corrosion_level * 0.02
            params['turbidity'] += corrosion_level * 5

        # 6. Disinfectant decay (affects chlorine)
        params['chlorine_residual'] *= np.random.uniform(0.4, 1.2)

        # Add natural variation
        for key in params:
            if key != 'coliform_status':
                params[key] *= np.random.uniform(0.95, 1.05)
                params[key] = round(params[key], 3)

        # Ensure physical constraints
        params['ph'] = np.clip(params['ph'], 4.0, 10.0)
        params['turbidity'] = max(0.1, params['turbidity'])
        params['tds'] = max(50, params['tds'])
        params['dissolved_oxygen'] = np.clip(params['dissolved_oxygen'] * np.random.uniform(0.8, 1.2), 2.0, 12.0)
        params['chlorine_residual'] = max(0, params['chlorine_residual'])

        # Hardness calculation
        params['calcium_hardness'] = params['total_hardness'] * np.random.uniform(0.6, 0.8)
        params['magnesium_hardness'] = params['total_hardness'] - params['calcium_hardness']

        return params

    def generate_samples(self, sites_df):
        """Generate water quality samples for all sites"""
        samples = []
        test_results = []

        start_date = datetime.now() - timedelta(days=365)  # 1 year ago

        print(f"\nGenerating {self.samples_per_site} samples per site...")

        for idx, site in sites_df.iterrows():
            # Track contamination history for trend modeling
            historical_contamination = []

            for month in range(self.samples_per_site):
                # Collection date (monthly)
                collection_date = start_date + timedelta(days=30 * month + np.random.randint(-5, 5))

                # Sample ID
                sample_id = f"WS-{site['site_code']}-{collection_date.strftime('%Y%m%d')}-{np.random.randint(1000, 9999):04X}"

                # Sample metadata
                sample = {
                    'sample_id': sample_id,
                    'site_code': site['site_code'],
                    'collection_date': collection_date,
                    'collection_time': f"{np.random.randint(8, 18):02d}:{np.random.randint(0, 60):02d}:00",
                    'collected_by': f"Technician {np.random.randint(1, 20):02d}",
                    'source_type': 'Surface Water',
                    'water_source_root': site['water_body_type'],
                    'weather': np.random.choice(['Sunny', 'Cloudy', 'Rainy'], p=[0.6, 0.3, 0.1]),
                    'status': 'completed',
                    'priority': np.random.choice(['normal', 'high', 'urgent'], p=[0.8, 0.15, 0.05])
                }

                samples.append(sample)

                # Generate test results
                params = self._generate_water_quality_params(site, month, historical_contamination)

                test_result = {
                    'sample_id': sample_id,
                    'test_date': collection_date + timedelta(hours=np.random.randint(2, 24)),
                    'tested_by': f"Lab Tech {np.random.randint(1, 15):02d}",
                    **params,  # Add all water quality parameters
                    'qc_status': 'approved',
                    'qc_approved_by': f"QC Officer {np.random.randint(1, 5):02d}"
                }

                test_results.append(test_result)

                # Track contamination for trends
                contamination_score = (params['turbidity'] / 50 + params['tds'] / 1000 +
                                     params['nitrate'] / 50) / 3
                historical_contamination.append(contamination_score)

            if (idx + 1) % 100 == 0:
                print(f"  Processed {idx + 1}/{len(sites_df)} sites...")

        print(f"\n✓ Generated {len(samples):,} samples and {len(test_results):,} test results")

        return pd.DataFrame(samples), pd.DataFrame(test_results)

    def calculate_contamination_scores(self, test_results_df):
        """Calculate contamination scores for analysis table"""
        analyses = []

        print(f"\nCalculating contamination scores...")

        for idx, test in test_results_df.iterrows():
            # Calculate individual contamination scores (0.0-1.0)

            # 1. Runoff/sediment score (turbidity, TDS)
            runoff_score = min(1.0, (test['turbidity'] / 50 + (test['tds'] - 150) / 500) / 2)

            # 2. Sewage ingress score (BOD, COD, nitrate, coliform)
            sewage_score = min(1.0, (test['bod'] / 30 + test['cod'] / 80 + test['nitrate'] / 50) / 3)
            if test['coliform_status'] == 'present':
                sewage_score = min(1.0, sewage_score + 0.3)

            # 3. Salt intrusion score (TDS, conductivity, chlorine)
            salt_score = min(1.0, ((test['tds'] - 150) / 800 + (test['conductivity'] - 300) / 1000) / 2)

            # 4. Pipe corrosion score (iron, lead, turbidity)
            corrosion_score = min(1.0, (test['iron'] / 1.5 + test['lead'] / 0.03 + test['turbidity'] / 30) / 3)

            # 5. Disinfectant decay score (chlorine)
            decay_score = max(0, 1.0 - test['chlorine_residual'] / 0.5)

            # Overall contamination level
            overall_score = (runoff_score + sewage_score + salt_score + corrosion_score + decay_score) / 5

            # WHO/BIS compliance
            who_compliant = (
                4.5 <= test['ph'] <= 8.5 and
                test['turbidity'] < 5 and
                test['tds'] < 500 and
                test['nitrate'] < 45 and
                test['iron'] < 0.3 and
                test['arsenic'] < 0.01 and
                test['lead'] < 0.01 and
                test['coliform_status'] == 'absent'
            )

            # Determine contamination type
            scores_dict = {
                'runoff_sediment': runoff_score,
                'sewage_ingress': sewage_score,
                'salt_intrusion': salt_score,
                'pipe_corrosion': corrosion_score,
                'disinfectant_decay': decay_score
            }
            primary_contamination = max(scores_dict, key=scores_dict.get)

            # Priority and recommendations
            if overall_score > 0.7:
                priority = 'urgent'
                immediate_actions = json.dumps(['Stop water usage', 'Investigate contamination source', 'Alert authorities'])
            elif overall_score > 0.4:
                priority = 'high'
                immediate_actions = json.dumps(['Enhanced monitoring', 'Treatment required', 'Public notification'])
            else:
                priority = 'normal'
                immediate_actions = json.dumps(['Routine monitoring', 'Preventive maintenance'])

            analysis = {
                'sample_id': test['sample_id'],
                'analysis_date': test['test_date'] + timedelta(hours=2),
                'overall_quality_score': round(1.0 - overall_score, 3),  # Higher = better
                'runoff_sediment_score': round(runoff_score, 3),
                'sewage_ingress_score': round(sewage_score, 3),
                'salt_intrusion_score': round(salt_score, 3),
                'pipe_corrosion_score': round(corrosion_score, 3),
                'disinfectant_decay_score': round(decay_score, 3),
                'primary_contamination_type': primary_contamination,
                'who_compliant': who_compliant,
                'bis_compliant': who_compliant,  # Simplified
                'immediate_actions': immediate_actions,
                'implementation_priority': priority,
                'follow_up_required': overall_score > 0.4,
                'analyzed_by': f"Analyst {np.random.randint(1, 10):02d}"
            }

            analyses.append(analysis)

            if (idx + 1) % 1000 == 0:
                print(f"  Processed {idx + 1}/{len(test_results_df)} analyses...")

        print(f"\n✓ Generated {len(analyses):,} analyses")

        return pd.DataFrame(analyses)

    def generate_complete_dataset(self, output_dir='demo_data'):
        """Generate complete dataset: sites, samples, tests, analyses"""
        import os
        os.makedirs(output_dir, exist_ok=True)

        print(f"\n{'='*70}")
        print(f"AMRIT SAROVAR SYNTHETIC DATA GENERATION")
        print(f"{'='*70}")

        # 1. Generate sites
        sites_df = self.generate_sites()
        sites_df.to_csv(f"{output_dir}/amrit_sarovar_sites.csv", index=False)
        print(f"✓ Saved: {output_dir}/amrit_sarovar_sites.csv")

        # 2. Generate samples and test results
        samples_df, test_results_df = self.generate_samples(sites_df)
        samples_df.to_csv(f"{output_dir}/water_samples.csv", index=False)
        test_results_df.to_csv(f"{output_dir}/test_results.csv", index=False)
        print(f"✓ Saved: {output_dir}/water_samples.csv")
        print(f"✓ Saved: {output_dir}/test_results.csv")

        # 3. Calculate contamination analyses
        analyses_df = self.calculate_contamination_scores(test_results_df)
        analyses_df.to_csv(f"{output_dir}/analyses.csv", index=False)
        print(f"✓ Saved: {output_dir}/analyses.csv")

        # 4. Generate summary statistics
        summary = {
            'generation_date': datetime.now().isoformat(),
            'total_sites': len(sites_df),
            'total_samples': len(samples_df),
            'total_test_results': len(test_results_df),
            'total_analyses': len(analyses_df),
            'date_range': {
                'start': samples_df['collection_date'].min().isoformat(),
                'end': samples_df['collection_date'].max().isoformat()
            },
            'site_distribution': {
                'by_state': sites_df['state'].value_counts().to_dict(),
                'by_environment': sites_df['environment_type'].value_counts().to_dict()
            },
            'quality_distribution': {
                'who_compliant': int(analyses_df['who_compliant'].sum()),
                'non_compliant': int((~analyses_df['who_compliant']).sum()),
                'urgent_priority': int((analyses_df['implementation_priority'] == 'urgent').sum()),
                'high_priority': int((analyses_df['implementation_priority'] == 'high').sum())
            },
            'contamination_types': analyses_df['primary_contamination_type'].value_counts().to_dict()
        }

        with open(f"{output_dir}/dataset_summary.json", 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        print(f"✓ Saved: {output_dir}/dataset_summary.json")

        print(f"\n{'='*70}")
        print(f"GENERATION COMPLETE!")
        print(f"{'='*70}")
        print(f"\nDataset Summary:")
        print(f"  Sites: {summary['total_sites']:,}")
        print(f"  Samples: {summary['total_samples']:,}")
        print(f"  Test Results: {summary['total_test_results']:,}")
        print(f"  Analyses: {summary['total_analyses']:,}")
        print(f"\nQuality Distribution:")
        print(f"  WHO Compliant: {summary['quality_distribution']['who_compliant']:,} ({summary['quality_distribution']['who_compliant']/summary['total_analyses']*100:.1f}%)")
        print(f"  Non-Compliant: {summary['quality_distribution']['non_compliant']:,} ({summary['quality_distribution']['non_compliant']/summary['total_analyses']*100:.1f}%)")
        print(f"  Urgent Priority: {summary['quality_distribution']['urgent_priority']:,}")
        print(f"  High Priority: {summary['quality_distribution']['high_priority']:,}")

        return {
            'sites': sites_df,
            'samples': samples_df,
            'test_results': test_results_df,
            'analyses': analyses_df,
            'summary': summary
        }


if __name__ == "__main__":
    # Generate demo dataset
    generator = AmritSarovarDataGenerator(
        num_sites=1000,
        samples_per_site=12,  # Monthly for 1 year
        seed=42
    )

    dataset = generator.generate_complete_dataset(output_dir='demo_data')

    print(f"\n✓ All data files saved to 'demo_data/' directory")
    print(f"✓ Ready for ML model training!")
