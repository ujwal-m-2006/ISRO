import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
import xgboost as xgb
import joblib
from datetime import datetime, timedelta
import logging
from typing import Dict, List, Optional, Tuple, Any

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SolarFlarePredictor:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.is_trained = False
        
    def prepare_features(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare features from raw solar observation data
        """
        # Create feature engineering columns
        features = data.copy()
        
        # Time-based features
        if 'timestamp' in features.columns:
            features['hour'] = features['timestamp'].dt.hour
            features['day_of_week'] = features['timestamp'].dt.dayofweek
            features['day_of_year'] = features['timestamp'].dt.dayofyear
            features['is_weekend'] = (features['day_of_week'] >= 5).astype(int)
        
        # Flux-based features
        if 'soft_xray_flux' in features.columns:
            features['log_soft_flux'] = np.log1p(features['soft_xray_flux'])
            features['soft_flux_change'] = features['soft_xray_flux'].diff().fillna(0)
            
        if 'hard_xray_flux' in features.columns:
            features['log_hard_flux'] = np.log1p(features['hard_xray_flux'])
            features['hard_flux_change'] = features['hard_xray_flux'].diff().fillna(0)
        
        # Combined features
        if 'soft_xray_flux' in features.columns and 'hard_xray_flux' in features.columns:
            features['flux_ratio'] = features['soft_xray_flux'] / (features['hard_xray_flux'] + 1e-10)
            features['total_flux'] = features['soft_xray_flux'] + features['hard_xray_flux']
        
        # Spectrum features
        if 'energy_spectrum' in features.columns:
            # Extract statistical features from energy spectrum
            features['spectrum_mean'] = features['energy_spectrum'].apply(lambda x: np.mean(x) if isinstance(x, list) else 0)
            features['spectrum_std'] = features['energy_spectrum'].apply(lambda x: np.std(x) if isinstance(x, list) else 0)
            features['spectrum_max'] = features['energy_spectrum'].apply(lambda x: np.max(x) if isinstance(x, list) else 0)
            features['spectrum_min'] = features['energy_spectrum'].apply(lambda x: np.min(x) if isinstance(x, list) else 0)
        
        # Photon count features
        if 'photon_count' in features.columns:
            features['log_photon_count'] = np.log1p(features['photon_count'])
            
        # Temperature features
        if 'temperature' in features.columns:
            features['log_temperature'] = np.log1p(features['temperature'])
        
        return features
    
    def create_target_labels(self, data: pd.DataFrame) -> pd.Series:
        """
        Create target labels for flare classification
        Based on NOAA flare classification standards:
        - A-class: < 1e-8 W/m²
        - B-class: 1e-8 to 1e-7 W/m²
        - C-class: 1e-7 to 1e-6 W/m²
        - M-class: 1e-6 to 1e-5 W/m²
        - X-class: > 1e-5 W/m²
        """
        if 'soft_xray_flux' not in data.columns:
            return pd.Series(['unknown'] * len(data))
        
        flux = data['soft_xray_flux']
        labels = []
        
        for f in flux:
            if pd.isna(f):
                labels.append('unknown')
            elif f < 1e-8:
                labels.append('A')
            elif f < 1e-7:
                labels.append('B')
            elif f < 1e-6:
                labels.append('C')
            elif f < 1e-5:
                labels.append('M')
            else:
                labels.append('X')
        
        return pd.Series(labels)
    
    def train_model(self, X: pd.DataFrame, y: pd.Series, model_type: str = 'xgboost') -> None:
        """
        Train the solar flare prediction model
        """
        logger.info(f"Training {model_type} model with {len(X)} samples")
        
        # Prepare features
        X_prepared = self.prepare_features(X)
        
        # Select only numeric features for training
        numeric_features = X_prepared.select_dtypes(include=[np.number]).columns.tolist()
        X_numeric = X_prepared[numeric_features]
        
        # Handle missing values
        X_numeric = X_numeric.fillna(0)
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X_numeric)
        
        # Encode labels
        y_encoded = self.label_encoder.fit_transform(y)
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_scaled, y_encoded, test_size=0.2, random_state=42, stratify=y_encoded
        )
        
        # Train model
        if model_type == 'random_forest':
            self.model = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                min_samples_split=5,
                random_state=42,
                class_weight='balanced'
            )
        elif model_type == 'gradient_boosting':
            self.model = GradientBoostingClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=5,
                random_state=42
            )
        else:  # xgboost
            self.model = xgb.XGBClassifier(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                objective='multi:softprob',
                eval_metric='mlogloss'
            )
        
        # Train the model
        self.model.fit(X_train, y_train)
        
        # Evaluate
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        logger.info(f"Model training completed. Accuracy: {accuracy:.3f}")
        
        # Store training metadata
        self.training_metadata = {
            'model_type': model_type,
            'training_date': datetime.now().isoformat(),
            'training_samples': len(X),
            'feature_count': len(numeric_features),
            'accuracy': float(accuracy),
            'classes': self.label_encoder.classes_.tolist()
        }
        
        self.is_trained = True
        
    def predict(self, X: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make predictions using the trained model
        Returns: (predicted_classes, prediction_probabilities)
        """
        if not self.is_trained:
            raise ValueError("Model must be trained before making predictions")
        
        # Prepare features
        X_prepared = self.prepare_features(X)
        
        # Select numeric features
        numeric_features = X_prepared.select_dtypes(include=[np.number]).columns.tolist()
        X_numeric = X_prepared[numeric_features]
        
        # Handle missing values
        X_numeric = X_numeric.fillna(0)
        
        # Scale features
        X_scaled = self.scaler.transform(X_numeric)
        
        # Make predictions
        if hasattr(self.model, 'predict_proba'):
            probabilities = self.model.predict_proba(X_scaled)
            predictions = self.model.predict(X_scaled)
        else:
            predictions = self.model.predict(X_scaled)
            probabilities = np.zeros((len(predictions), len(self.label_encoder.classes_)))
        
        # Convert predictions back to original labels
        predicted_labels = self.label_encoder.inverse_transform(predictions)
        
        return predicted_labels, probabilities
    
    def save_model(self, filepath: str) -> None:
        """
        Save the trained model and preprocessing objects
        """
        model_data = {
            'model': self.model,
            'scaler': self.scaler,
            'label_encoder': self.label_encoder,
            'is_trained': self.is_trained,
            'training_metadata': getattr(self, 'training_metadata', {})
        }
        
        joblib.dump(model_data, filepath)
        logger.info(f"Model saved to {filepath}")
    
    def load_model(self, filepath: str) -> None:
        """
        Load a trained model
        """
        model_data = joblib.load(filepath)
        
        self.model = model_data['model']
        self.scaler = model_data['scaler']
        self.label_encoder = model_data['label_encoder']
        self.is_trained = model_data['is_trained']
        
        if 'training_metadata' in model_data:
            self.training_metadata = model_data['training_metadata']
        
        logger.info(f"Model loaded from {filepath}")
    
    def get_feature_importance(self) -> Optional[pd.DataFrame]:
        """
        Get feature importance from the trained model
        """
        if not self.is_trained or not hasattr(self.model, 'feature_importances_'):
            return None
        
        # Get feature names
        # This is simplified - in practice you'd need to track which features were used
        feature_names = [f'feature_{i}' for i in range(len(self.model.feature_importances_))]
        
        return pd.DataFrame({
            'feature': feature_names,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)

# Example usage and training script
if __name__ == "__main__":
    # This would be called with real solar data
    # For demonstration, create synthetic data
    
    # Generate synthetic solar flare data
    np.random.seed(42)
    n_samples = 1000
    
    # Create synthetic features
    data = {
        'timestamp': pd.date_range('2023-01-01', periods=n_samples, freq='H'),
        'soft_xray_flux': np.random.lognormal(15, 1, n_samples) * 1e-9,  # A-X class range
        'hard_xray_flux': np.random.lognormal(12, 0.8, n_samples) * 1e-9,
        'photon_count': np.random.poisson(1000, n_samples),
        'temperature': np.random.normal(10, 2, n_samples),  # in MK
    }
    
    # Add some realistic patterns
    for i in range(n_samples):
        if i % 100 == 0:  # Simulate flares every 100 hours
            data['soft_xray_flux'][i] *= 100
            data['hard_xray_flux'][i] *= 50
            data['photon_count'][i] += 500
    
    df = pd.DataFrame(data)
    
    # Create target labels
    predictor = SolarFlarePredictor()
    y = predictor.create_target_labels(df)
    
    # Train model
    predictor.train_model(df, y, model_type='xgboost')
    
    # Save model
    predictor.save_model('solar_flare_model.pkl')
    
    # Make predictions on sample data
    sample_data = df.iloc[:10]
    predictions, probabilities = predictor.predict(sample_data)
    
    print("Sample predictions:")
    for i in range(min(5, len(predictions))):
        print(f"{i+1}: Predicted {predictions[i]}, Probabilities: {probabilities[i]}")