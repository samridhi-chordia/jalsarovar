#!/usr/bin/env python3
"""
Train All ML Models for Water Quality Optimization
Trains: Site Risk Classifier, Contamination Classifier, Quality Forecaster, Schedule Optimizer
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
import joblib
import warnings
warnings.filterwarnings('ignore')

# ML libraries
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import (classification_report, confusion_matrix, accuracy_score,
                             mean_squared_error, r2_score, mean_absolute_error)
from sklearn.preprocessing import LabelEncoder

# XGBoost (research paper requirement for contamination classification)
try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    print("WARNING: XGBoost not installed. Using GradientBoostingClassifier as fallback.")
    print("Install with: pip install xgboost")
    XGBOOST_AVAILABLE = False

# Import feature engineering
import sys
sys.path.append('/Users/test/jalsarovar')
from app.ml.feature_engineering import WaterQualityFeatureEngineer, load_demo_data


class MLModelTrainer:
    """Train and evaluate all ML models"""

    def __init__(self, output_dir='app/ml/trained_models'):
        self.output_dir = output_dir
        self.models = {}
        self.metrics = {}
        self.engineer = WaterQualityFeatureEngineer()

        import os
        os.makedirs(output_dir, exist_ok=True)

        print(f"ML Model Trainer Initialized")
        print(f"Output directory: {output_dir}")

    def train_site_risk_classifier(self, sites_df, test_results_df, analyses_df):
        """
        MODEL 1: Site Risk Prediction (High/Medium/Low)

        Predicts which sites need frequent vs infrequent testing based on:
        - Site characteristics (environment, proximity to contamination sources)
        - Historical contamination patterns
        - Population density
        """
        print("\n" + "="*70)
        print("MODEL 1: SITE RISK CLASSIFIER")
        print("="*70)

        # Engineer features
        site_features = self.engineer.engineer_site_features(sites_df, test_results_df, analyses_df)

        # Create risk labels based on historical contamination
        # High risk: Average quality score < 0.5, Medium: 0.5-0.7, Low: > 0.7
        if 'hist_overall_quality_score_mean' in site_features.columns:
            site_features['risk_level'] = site_features['hist_overall_quality_score_mean'].apply(
                lambda x: 'high' if x < 0.5 else ('medium' if x < 0.7 else 'low')
            )
        else:
            # Fallback: Use environment type as proxy
            risk_mapping = {
                'Urban': 'high',
                'Industrial': 'high',
                'Semi-Urban': 'medium',
                'Rural Agricultural': 'medium',
                'Rural': 'low'
            }
            site_features['risk_level'] = site_features['environment_type'].map(risk_mapping)

        # Prepare training data
        feature_cols = [col for col in site_features.columns if col.endswith('_encoded') or
                       col.endswith('_binary') or col.endswith('_log') or col.startswith('hist_') or
                       col.startswith('is_') or col == 'population_density']

        X = site_features[feature_cols].fillna(0).values
        y = site_features['risk_level'].values

        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

        # Train Random Forest
        print(f"\nTraining Random Forest Classifier...")
        print(f"  Training samples: {len(X_train)}")
        print(f"  Test samples: {len(X_test)}")
        print(f"  Features: {len(feature_cols)}")

        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1
        )

        model.fit(X_train, y_train)

        # Evaluate
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)

        # Cross-validation
        cv_scores = cross_val_score(model, X_train, y_train, cv=5)

        print(f"\n✓ Model trained successfully!")
        print(f"  Accuracy: {accuracy:.3f}")
        print(f"  CV Score: {cv_scores.mean():.3f} (+/- {cv_scores.std():.3f})")

        print(f"\nClassification Report:")
        print(classification_report(y_test, y_pred))

        # Feature importance
        importances = pd.DataFrame({
            'feature': feature_cols,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False).head(10)

        print(f"\nTop 10 Feature Importances:")
        for idx, row in importances.iterrows():
            print(f"  {row['feature']}: {row['importance']:.4f}")

        # Save model
        model_path = f"{self.output_dir}/site_risk_classifier.pkl"
        joblib.dump(model, model_path)
        print(f"\n✓ Model saved: {model_path}")

        self.models['site_risk_classifier'] = model
        self.metrics['site_risk_classifier'] = {
            'accuracy': float(accuracy),
            'cv_score_mean': float(cv_scores.mean()),
            'cv_score_std': float(cv_scores.std()),
            'feature_importances': importances.to_dict('records'),
            'confusion_matrix': confusion_matrix(y_test, y_pred).tolist(),
            'classification_report': classification_report(y_test, y_pred, output_dict=True)
        }

        return model, site_features

    def train_contamination_classifier(self, samples_df, test_results_df, sites_df, analyses_df):
        """
        MODEL 2: Contamination Type Classification

        Predicts the primary contamination source from water quality parameters:
        - Runoff/sediment
        - Sewage ingress
        - Salt intrusion
        - Pipe corrosion
        - Disinfectant decay
        """
        print("\n" + "="*70)
        print("MODEL 2: CONTAMINATION TYPE CLASSIFIER")
        print("="*70)

        # Engineer features
        sample_features = self.engineer.engineer_sample_features(samples_df, test_results_df, sites_df)

        # Merge with analyses to get contamination labels
        sample_features = sample_features.merge(
            analyses_df[['sample_id', 'primary_contamination_type']], on='sample_id', how='inner'
        )

        # Prepare training data (use water quality parameters)
        feature_cols = ['ph', 'temperature', 'turbidity', 'tds', 'conductivity', 'total_hardness',
                       'chlorine_residual', 'dissolved_oxygen', 'bod', 'cod', 'nitrate', 'fluoride',
                       'iron', 'arsenic', 'lead', 'coliform_present', 'is_monsoon',
                       'industrial_nearby', 'agricultural_nearby', 'is_coastal',
                       'bod_cod_ratio', 'hardness_tds_ratio', 'composite_risk_score']

        # Ensure all features exist
        feature_cols = [col for col in feature_cols if col in sample_features.columns]

        X = sample_features[feature_cols].fillna(0).values
        y = sample_features['primary_contamination_type'].values

        # Encode labels for XGBoost (requires integer labels)
        label_encoder = LabelEncoder()
        y_encoded = label_encoder.fit_transform(y)

        # Train-test split
        X_train, X_test, y_train, y_test = train_test_split(X, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded)

        # Train XGBoost Classifier (research paper requirement)
        if XGBOOST_AVAILABLE:
            print(f"\nTraining XGBoost Classifier...")
            print(f"  Training samples: {len(X_train)}")
            print(f"  Test samples: {len(X_test)}")
            print(f"  Features: {len(feature_cols)}")
            print(f"  Classes: {list(label_encoder.classes_)}")

            model = XGBClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=42,
                use_label_encoder=False,
                eval_metric='mlogloss'
            )
        else:
            # Fallback to Gradient Boosting if XGBoost not available
            print(f"\nTraining Gradient Boosting Classifier (XGBoost not available)...")
            print(f"  Training samples: {len(X_train)}")
            print(f"  Test samples: {len(X_test)}")
            print(f"  Features: {len(feature_cols)}")
            print(f"  Classes: {list(label_encoder.classes_)}")

            model = GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=42
            )

        model.fit(X_train, y_train)

        # Evaluate
        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)

        # Cross-validation
        cv_scores = cross_val_score(model, X_train, y_train, cv=5)

        print(f"\n✓ Model trained successfully!")
        print(f"  Accuracy: {accuracy:.3f}")
        print(f"  CV Score: {cv_scores.mean():.3f} (+/- {cv_scores.std():.3f})")

        # Decode labels for classification report
        y_test_labels = label_encoder.inverse_transform(y_test)
        y_pred_labels = label_encoder.inverse_transform(y_pred)

        print(f"\nClassification Report:")
        print(classification_report(y_test_labels, y_pred_labels))

        # Feature importance
        importances = pd.DataFrame({
            'feature': feature_cols,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False).head(10)

        print(f"\nTop 10 Feature Importances:")
        for idx, row in importances.iterrows():
            print(f"  {row['feature']}: {row['importance']:.4f}")

        # Save model with label encoder
        model_path = f"{self.output_dir}/contamination_classifier.pkl"
        joblib.dump({'model': model, 'label_encoder': label_encoder, 'feature_cols': feature_cols}, model_path)
        print(f"\n✓ Model saved: {model_path}")

        self.models['contamination_classifier'] = model
        self.metrics['contamination_classifier'] = {
            'accuracy': float(accuracy),
            'cv_score_mean': float(cv_scores.mean()),
            'cv_score_std': float(cv_scores.std()),
            'feature_importances': importances.to_dict('records'),
            'classification_report': classification_report(y_test_labels, y_pred_labels, output_dict=True)
        }

        return model

    def train_quality_forecaster(self, samples_df, test_results_df, parameter='ph'):
        """
        MODEL 3: Water Quality Forecasting

        Predicts future water quality parameter values based on historical trends
        Uses time-series features and rolling statistics
        """
        print("\n" + "="*70)
        print(f"MODEL 3: QUALITY FORECASTER (parameter: {parameter})")
        print("="*70)

        # Create time-series features
        ts_features = self.engineer.create_time_series_features(
            samples_df, test_results_df, parameter=parameter, window_size=3
        )

        if len(ts_features) < 100:
            print(f"\n⚠ Warning: Insufficient time-series data ({len(ts_features)} samples)")
            print(f"  Need at least 100 samples for reliable forecasting")
            return None

        # Prepare training data
        feature_cols = [col for col in ts_features.columns if col.startswith(f'{parameter}_')]
        feature_cols = [col for col in feature_cols if col != 'target_value']

        X = ts_features[feature_cols].fillna(0).values
        y = ts_features['target_value'].values

        # Train-test split (time-series: no shuffling)
        split_idx = int(len(X) * 0.8)
        X_train, X_test = X[:split_idx], X[split_idx:]
        y_train, y_test = y[:split_idx], y[split_idx:]

        # Train Random Forest Regressor
        print(f"\nTraining Random Forest Regressor...")
        print(f"  Training samples: {len(X_train)}")
        print(f"  Test samples: {len(X_test)}")
        print(f"  Features: {len(feature_cols)}")

        model = RandomForestRegressor(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1
        )

        model.fit(X_train, y_train)

        # Evaluate
        y_pred = model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)

        print(f"\n✓ Model trained successfully!")
        print(f"  RMSE: {rmse:.4f}")
        print(f"  MAE: {mae:.4f}")
        print(f"  R²: {r2:.4f}")

        # Feature importance
        importances = pd.DataFrame({
            'feature': feature_cols,
            'importance': model.feature_importances_
        }).sort_values('importance', ascending=False).head(10)

        print(f"\nTop 10 Feature Importances:")
        for idx, row in importances.iterrows():
            print(f"  {row['feature']}: {row['importance']:.4f}")

        # Save model
        model_path = f"{self.output_dir}/quality_forecaster_{parameter}.pkl"
        joblib.dump(model, model_path)
        print(f"\n✓ Model saved: {model_path}")

        self.models[f'quality_forecaster_{parameter}'] = model
        self.metrics[f'quality_forecaster_{parameter}'] = {
            'rmse': float(rmse),
            'mae': float(mae),
            'r2': float(r2),
            'feature_importances': importances.to_dict('records')
        }

        return model

    def create_testing_schedule_optimizer(self, site_features):
        """
        MODEL 4: Testing Schedule Optimizer

        Creates optimal testing schedule based on site risk levels
        Uses rule-based optimization with ML risk predictions
        """
        print("\n" + "="*70)
        print("MODEL 4: TESTING SCHEDULE OPTIMIZER")
        print("="*70)

        # Get risk predictions from Model 1
        if 'site_risk_classifier' not in self.models:
            print("⚠ Site risk classifier not trained yet. Skipping schedule optimizer.")
            return None

        model = self.models['site_risk_classifier']

        # Extract features for prediction
        feature_cols = [col for col in site_features.columns if col.endswith('_encoded') or
                       col.endswith('_binary') or col.endswith('_log') or col.startswith('hist_') or
                       col.startswith('is_') or col == 'population_density']

        X = site_features[feature_cols].fillna(0).values

        # Predict risk levels
        risk_predictions = model.predict(X)
        site_features['predicted_risk'] = risk_predictions

        # Create testing schedule
        schedule_mapping = {
            'high': 12,      # Monthly
            'medium': 4,     # Quarterly
            'low': 1         # Annually
        }

        site_features['tests_per_year'] = site_features['predicted_risk'].map(schedule_mapping)

        # Calculate cost savings
        baseline_tests = len(site_features) * 12  # All sites monthly
        optimized_tests = site_features['tests_per_year'].sum()
        tests_saved = baseline_tests - optimized_tests
        savings_percent = (tests_saved / baseline_tests) * 100

        print(f"\n✓ Testing schedule created!")
        print(f"\nRisk Distribution:")
        for risk_level in ['high', 'medium', 'low']:
            count = (site_features['predicted_risk'] == risk_level).sum()
            percent = (count / len(site_features)) * 100
            tests = count * schedule_mapping[risk_level]
            print(f"  {risk_level.upper()}: {count} sites ({percent:.1f}%) → {tests} tests/year")

        print(f"\nCost Optimization:")
        print(f"  Baseline tests: {baseline_tests:,}")
        print(f"  Optimized tests: {optimized_tests:,}")
        print(f"  Tests saved: {tests_saved:,} ({savings_percent:.1f}%)")

        # Save schedule
        schedule_df = site_features[['site_code', 'site_name', 'predicted_risk', 'tests_per_year']]
        schedule_path = f"{self.output_dir}/testing_schedule.csv"
        schedule_df.to_csv(schedule_path, index=False)
        print(f"\n✓ Schedule saved: {schedule_path}")

        self.metrics['testing_schedule_optimizer'] = {
            'total_sites': len(site_features),
            'risk_distribution': site_features['predicted_risk'].value_counts().to_dict(),
            'baseline_tests': baseline_tests,
            'optimized_tests': int(optimized_tests),
            'tests_saved': tests_saved,
            'savings_percent': float(savings_percent)
        }

        return schedule_df

    def generate_model_report(self, output_path='reports/ml_model_report.json'):
        """Generate comprehensive model performance report"""

        report = {
            'generation_date': datetime.now().isoformat(),
            'models_trained': list(self.models.keys()),
            'metrics': self.metrics,
            'summary': {
                'site_risk_classifier': {
                    'status': 'trained' if 'site_risk_classifier' in self.models else 'not trained',
                    'accuracy': self.metrics.get('site_risk_classifier', {}).get('accuracy', 0)
                },
                'contamination_classifier': {
                    'status': 'trained' if 'contamination_classifier' in self.models else 'not trained',
                    'accuracy': self.metrics.get('contamination_classifier', {}).get('accuracy', 0)
                },
                'quality_forecaster': {
                    'status': 'trained' if any('forecaster' in k for k in self.models.keys()) else 'not trained',
                    'rmse': self.metrics.get('quality_forecaster_ph', {}).get('rmse', 0)
                },
                'testing_schedule_optimizer': {
                    'status': 'created' if 'testing_schedule_optimizer' in self.metrics else 'not created',
                    'savings_percent': self.metrics.get('testing_schedule_optimizer', {}).get('savings_percent', 0)
                }
            }
        }

        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        print(f"\n✓ Model report saved: {output_path}")

        return report


def main():
    """Train all ML models"""

    print("\n" + "="*70)
    print("WATER QUALITY ML MODELS - TRAINING PIPELINE")
    print("="*70 + "\n")

    # Load data
    sites_df, samples_df, test_results_df, analyses_df = load_demo_data()

    # Initialize trainer
    trainer = MLModelTrainer()

    # Train Model 1: Site Risk Classifier
    model1, site_features = trainer.train_site_risk_classifier(sites_df, test_results_df, analyses_df)

    # Train Model 2: Contamination Classifier
    model2 = trainer.train_contamination_classifier(samples_df, test_results_df, sites_df, analyses_df)

    # Train Model 3: Quality Forecaster (pH)
    model3 = trainer.train_quality_forecaster(samples_df, test_results_df, parameter='ph')

    # Create Model 4: Testing Schedule Optimizer
    schedule = trainer.create_testing_schedule_optimizer(site_features)

    # Generate report
    print("\n" + "="*70)
    print("GENERATING MODEL REPORT")
    print("="*70)

    report = trainer.generate_model_report()

    print("\n" + "="*70)
    print("ALL MODELS TRAINED SUCCESSFULLY!")
    print("="*70 + "\n")

    print("Model Summary:")
    for model_name, model_info in report['summary'].items():
        status = "✓" if model_info['status'] in ['trained', 'created'] else "✗"
        print(f"  {status} {model_name}: {model_info['status']}")
        if 'accuracy' in model_info and model_info['accuracy'] > 0:
            print(f"      Accuracy: {model_info['accuracy']:.3f}")
        if 'rmse' in model_info and model_info['rmse'] > 0:
            print(f"      RMSE: {model_info['rmse']:.4f}")
        if 'savings_percent' in model_info and model_info['savings_percent'] > 0:
            print(f"      Cost Savings: {model_info['savings_percent']:.1f}%")

    print(f"\nAll trained models saved to: {trainer.output_dir}/")


if __name__ == "__main__":
    main()
