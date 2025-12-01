#!/usr/bin/env python3
"""
Feature Engineering Pipeline for Water Quality ML Models
Creates features from raw data for training and inference
"""

import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.preprocessing import LabelEncoder, StandardScaler
import warnings
warnings.filterwarnings('ignore')


class WaterQualityFeatureEngineer:
    """Extract and engineer features for ML models"""

    def __init__(self):
        self.label_encoders = {}
        self.scaler = StandardScaler()
        self.feature_names = None

    def engineer_site_features(self, sites_df, test_results_df, analyses_df):
        """
        Create site-level features for risk prediction

        Args:
            sites_df: Site metadata
            test_results_df: Historical test results
            analyses_df: Historical contamination analyses

        Returns:
            DataFrame with engineered features
        """
        print("Engineering site features...")

        features = sites_df.copy()

        # Encode categorical variables
        categorical_cols = ['environment_type', 'water_body_type', 'state']
        for col in categorical_cols:
            if col not in self.label_encoders:
                self.label_encoders[col] = LabelEncoder()
                features[f'{col}_encoded'] = self.label_encoders[col].fit_transform(features[col])
            else:
                features[f'{col}_encoded'] = self.label_encoders[col].transform(features[col])

        # Binary features
        features['is_coastal_binary'] = features['is_coastal'].astype(int)
        features['industrial_nearby_binary'] = features['industrial_nearby'].astype(int)
        features['agricultural_nearby_binary'] = features['agricultural_nearby'].astype(int)

        # Population density bins
        features['pop_density_log'] = np.log1p(features['population_density'])
        features['is_high_density'] = (features['population_density'] > 5000).astype(int)

        # Historical contamination statistics (if available)
        if not analyses_df.empty:
            # Merge site_code with sample_id to analyses
            sample_site_map = test_results_df[['sample_id']].merge(
                pd.read_csv('demo_data/water_samples.csv')[['sample_id', 'site_code']],
                on='sample_id', how='left'
            )

            analyses_with_sites = analyses_df.merge(sample_site_map, on='sample_id', how='left')

            # Calculate aggregated contamination metrics per site
            contamination_stats = analyses_with_sites.groupby('site_code').agg({
                'overall_quality_score': ['mean', 'std', 'min'],
                'runoff_sediment_score': 'mean',
                'sewage_ingress_score': 'mean',
                'salt_intrusion_score': 'mean',
                'pipe_corrosion_score': 'mean',
                'disinfectant_decay_score': 'mean',
                'who_compliant': 'mean',
                'follow_up_required': 'sum'
            }).reset_index()

            contamination_stats.columns = ['site_code'] + [
                f'hist_{col[0]}_{col[1]}' if col[1] else f'hist_{col[0]}'
                for col in contamination_stats.columns[1:]
            ]

            features = features.merge(contamination_stats, on='site_code', how='left')

            # Fill NaN for sites without history
            for col in contamination_stats.columns:
                if col != 'site_code' and col in features.columns:
                    features[col] = features[col].fillna(features[col].median())

        print(f"✓ Created {len(features.columns)} site features")

        return features

    def engineer_sample_features(self, samples_df, test_results_df, sites_df):
        """
        Create sample-level features for contamination classification

        Args:
            samples_df: Water samples
            test_results_df: Test results
            sites_df: Site metadata

        Returns:
            DataFrame with engineered features
        """
        print("Engineering sample features...")

        # Merge all data
        features = samples_df.merge(test_results_df, on='sample_id', how='inner')
        features = features.merge(sites_df[['site_code', 'environment_type', 'industrial_nearby',
                                           'agricultural_nearby', 'is_coastal', 'population_density']],
                                 on='site_code', how='left')

        # Temporal features
        features['collection_date'] = pd.to_datetime(features['collection_date'])
        features['month'] = features['collection_date'].dt.month
        features['season'] = features['month'].apply(lambda m:
            'winter' if m in [12, 1, 2] else
            'spring' if m in [3, 4, 5] else
            'monsoon' if m in [6, 7, 8, 9] else
            'autumn'
        )
        features['is_monsoon'] = (features['season'] == 'monsoon').astype(int)
        features['day_of_year'] = features['collection_date'].dt.dayofyear

        # Encode categorical
        if 'season' not in self.label_encoders:
            self.label_encoders['season'] = LabelEncoder()
            features['season_encoded'] = self.label_encoders['season'].fit_transform(features['season'])
        else:
            features['season_encoded'] = self.label_encoders['season'].transform(features['season'])

        # Water quality ratios (domain knowledge)
        features['bod_cod_ratio'] = features['bod'] / (features['cod'] + 0.1)
        features['hardness_tds_ratio'] = features['total_hardness'] / (features['tds'] + 1)
        features['do_temperature_adjusted'] = features['dissolved_oxygen'] / (features['temperature'] + 1)

        # Contamination indicators
        features['high_turbidity'] = (features['turbidity'] > 10).astype(int)
        features['high_nitrate'] = (features['nitrate'] > 45).astype(int)
        features['high_tds'] = (features['tds'] > 500).astype(int)
        features['coliform_present'] = (features['coliform_status'] == 'present').astype(int)
        features['high_iron'] = (features['iron'] > 0.3).astype(int)
        features['high_arsenic'] = (features['arsenic'] > 0.01).astype(int)
        features['high_lead'] = (features['lead'] > 0.01).astype(int)

        # Combined risk score (simple heuristic)
        features['composite_risk_score'] = (
            features['high_turbidity'] +
            features['high_nitrate'] +
            features['high_tds'] +
            features['coliform_present'] +
            features['high_iron'] +
            features['high_arsenic'] +
            features['high_lead']
        ) / 7.0

        print(f"✓ Created {len(features.columns)} sample features")

        return features

    def create_time_series_features(self, samples_df, test_results_df, parameter='ph', window_size=3):
        """
        Create time-series features for forecasting

        Args:
            samples_df: Water samples with dates
            test_results_df: Test results
            parameter: Which parameter to forecast (default: 'ph')
            window_size: Lookback window for features

        Returns:
            DataFrame with time-series features
        """
        print(f"Creating time-series features for parameter: {parameter}")

        # Merge and sort by date
        ts_data = samples_df[['sample_id', 'site_code', 'collection_date']].merge(
            test_results_df[['sample_id', parameter]], on='sample_id', how='inner'
        )
        ts_data['collection_date'] = pd.to_datetime(ts_data['collection_date'])
        ts_data = ts_data.sort_values(['site_code', 'collection_date'])

        features_list = []

        for site_code in ts_data['site_code'].unique():
            site_data = ts_data[ts_data['site_code'] == site_code].copy()

            # Skip if insufficient data
            if len(site_data) < window_size + 1:
                continue

            for i in range(window_size, len(site_data)):
                feature_row = {
                    'site_code': site_code,
                    'target_date': site_data.iloc[i]['collection_date'],
                    'target_value': site_data.iloc[i][parameter]
                }

                # Lagged values
                for lag in range(1, window_size + 1):
                    feature_row[f'{parameter}_lag_{lag}'] = site_data.iloc[i - lag][parameter]

                # Rolling statistics
                window_values = site_data.iloc[i - window_size:i][parameter].values
                feature_row[f'{parameter}_rolling_mean'] = np.mean(window_values)
                feature_row[f'{parameter}_rolling_std'] = np.std(window_values)
                feature_row[f'{parameter}_rolling_min'] = np.min(window_values)
                feature_row[f'{parameter}_rolling_max'] = np.max(window_values)

                # Trend
                feature_row[f'{parameter}_trend'] = (
                    site_data.iloc[i - 1][parameter] - site_data.iloc[i - window_size][parameter]
                ) / window_size

                features_list.append(feature_row)

        features_df = pd.DataFrame(features_list)

        print(f"✓ Created time-series features for {len(features_df)} samples")

        return features_df

    def prepare_training_data(self, features_df, target_col, feature_cols=None, scale=True):
        """
        Prepare features and target for model training

        Args:
            features_df: DataFrame with all features
            target_col: Name of target column
            feature_cols: List of feature column names (None = auto-select numeric)
            scale: Whether to standardize features

        Returns:
            X_train, y_train, feature_names
        """
        if feature_cols is None:
            # Auto-select numeric features
            feature_cols = features_df.select_dtypes(include=[np.number]).columns.tolist()
            if target_col in feature_cols:
                feature_cols.remove(target_col)

        X = features_df[feature_cols].fillna(0).values
        y = features_df[target_col].values

        if scale:
            X = self.scaler.fit_transform(X)

        self.feature_names = feature_cols

        print(f"✓ Training data prepared: {X.shape[0]} samples × {X.shape[1]} features")

        return X, y, feature_cols

    def calculate_feature_importance_scores(self, model, top_n=20):
        """Calculate and display feature importance"""
        if hasattr(model, 'feature_importances_'):
            importances = model.feature_importances_
            indices = np.argsort(importances)[::-1][:top_n]

            print(f"\nTop {top_n} Feature Importances:")
            for i, idx in enumerate(indices, 1):
                print(f"  {i}. {self.feature_names[idx]}: {importances[idx]:.4f}")

            return pd.DataFrame({
                'feature': [self.feature_names[i] for i in indices],
                'importance': importances[indices]
            })

        return None


def load_demo_data():
    """Load generated demo data"""
    print("Loading demo data...")

    sites_df = pd.read_csv('demo_data/amrit_sarovar_sites.csv')
    samples_df = pd.read_csv('demo_data/water_samples.csv')
    test_results_df = pd.read_csv('demo_data/test_results.csv')
    analyses_df = pd.read_csv('demo_data/analyses.csv')

    print(f"✓ Loaded:")
    print(f"  Sites: {len(sites_df):,}")
    print(f"  Samples: {len(samples_df):,}")
    print(f"  Test Results: {len(test_results_df):,}")
    print(f"  Analyses: {len(analyses_df):,}")

    return sites_df, samples_df, test_results_df, analyses_df


if __name__ == "__main__":
    # Test feature engineering pipeline
    print("\n" + "="*70)
    print("FEATURE ENGINEERING PIPELINE TEST")
    print("="*70 + "\n")

    # Load data
    sites_df, samples_df, test_results_df, analyses_df = load_demo_data()

    # Initialize engineer
    engineer = WaterQualityFeatureEngineer()

    # Engineer site features
    print("\n--- SITE FEATURES ---")
    site_features = engineer.engineer_site_features(sites_df, test_results_df, analyses_df)
    print(f"Site features shape: {site_features.shape}")
    print(f"Columns: {list(site_features.columns[:10])}...")

    # Engineer sample features
    print("\n--- SAMPLE FEATURES ---")
    sample_features = engineer.engineer_sample_features(samples_df, test_results_df, sites_df)
    print(f"Sample features shape: {sample_features.shape}")
    print(f"Columns: {list(sample_features.columns[:10])}...")

    # Create time-series features
    print("\n--- TIME-SERIES FEATURES ---")
    ts_features = engineer.create_time_series_features(samples_df, test_results_df, parameter='ph')
    print(f"Time-series features shape: {ts_features.shape}")

    print("\n" + "="*70)
    print("FEATURE ENGINEERING COMPLETE!")
    print("="*70)
