import sys
import os
import logging
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add backend directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import database configuration
from database import SQLALCHEMY_DATABASE_URL

# Import models
from models import SoLEXSObservation, HEL1OSObservation

# Import predictor
from ml_models.solar_flare_predictor import SolarFlarePredictor


def load_solar_data(db_url: str, days_back: int = 365) -> pd.DataFrame:
    """
    Load solar observation data from database for training
    """
    try:
        # Create database engine
        engine = create_engine(db_url)
        
        # Get date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Query SoLEXS observations
        solexs_query = f"""
            SELECT 
                timestamp,
                soft_xray_flux,
                energy_spectrum,
                photon_count,
                temperature,
                observation_time,
                detector_health,
                quality_flag,
                instrument_status
            FROM solexs_observations 
            WHERE timestamp >= '{start_date.isoformat()}'
            ORDER BY timestamp DESC
        """
        
        # Query HEL1OS observations
        hel1os_query = f"""
            SELECT 
                timestamp,
                hard_xray_flux,
                energy_distribution,
                detector_count,
                peak_energy,
                observation_time,
                detector_health,
                quality_flag,
                instrument_status
            FROM hel1os_observations 
            WHERE timestamp >= '{start_date.isoformat()}'
            ORDER BY timestamp DESC
        """
        
        # Load data
        solexs_df = pd.read_sql(solexs_query, engine)
        hel1os_df = pd.read_sql(hel1os_query, engine)
        
        logger.info(f"Loaded {len(solexs_df)} SoLEXS observations and {len(hel1os_df)} HEL1OS observations")
        
        # Merge data on timestamp (approximate matching)
        if not solexs_df.empty and not hel1os_df.empty:
            # Create merged dataset
            merged_df = pd.merge(
                solexs_df, 
                hel1os_df, 
                on='timestamp', 
                how='outer',
                suffixes=('_solexs', '_hel1os')
            )
        else:
            merged_df = solexs_df if not solexs_df.empty else hel1os_df
        
        return merged_df
        
    except Exception as e:
        logger.error(f"Error loading solar data: {e}")
        return pd.DataFrame()


def train_solar_flare_model():
    """
    Train the solar flare prediction model with real data
    """
    logger.info("Starting solar flare model training...")
    
    # Load data
    df = load_solar_data(SQLALCHEMY_DATABASE_URL)
    
    if df.empty:
        logger.warning("No solar data available for training. Using synthetic data.")
        # Create synthetic data for demonstration
        import numpy as np
        import pandas as pd
        
        n_samples = 5000
        np.random.seed(42)
        
        data = {
            'timestamp': pd.date_range('2023-01-01', periods=n_samples, freq='H'),
            'soft_xray_flux': np.random.lognormal(15, 1, n_samples) * 1e-9,
            'hard_xray_flux': np.random.lognormal(12, 0.8, n_samples) * 1e-9,
            'photon_count': np.random.poisson(1000, n_samples),
            'temperature': np.random.normal(10, 2, n_samples),
        }
        
        # Add realistic flare patterns
        for i in range(n_samples):
            if i % 200 == 0:
                data['soft_xray_flux'][i] *= 100
                data['hard_xray_flux'][i] *= 50
                data['photon_count'][i] += 500
        
        df = pd.DataFrame(data)
    
    # Initialize predictor
    predictor = SolarFlarePredictor()
    
    # Create target labels
    y = predictor.create_target_labels(df)
    
    # Train model
    predictor.train_model(df, y, model_type='xgboost')
    
    # Save model
    model_path = 'models/solar_flare_model.pkl'
    os.makedirs('models', exist_ok=True)
    predictor.save_model(model_path)
    
    logger.info(f"Model trained and saved to {model_path}")
    
    # Print training summary
    metadata = getattr(predictor, 'training_metadata', {})
    logger.info(f"Training Summary:")
    logger.info(f"  Model type: {metadata.get('model_type', 'unknown')}")
    logger.info(f"  Training samples: {metadata.get('training_samples', 0)}")
    logger.info(f"  Accuracy: {metadata.get('accuracy', 0):.3f}")
    logger.info(f"  Classes: {metadata.get('classes', [])}")
    
    return predictor


if __name__ == "__main__":
    # Train the model
    predictor = train_solar_flare_model()
    
    # Test prediction with sample data
    if not predictor.is_trained:
        logger.error("Model training failed")
        sys.exit(1)
    
    # Make sample prediction
    sample_data = {
        'timestamp': [datetime.now()],
        'soft_xray_flux': [1.2e-6],
        'hard_xray_flux': [3.8e-7],
        'photon_count': [1245892],
        'temperature': [12.5]
    }
    
    sample_df = pd.DataFrame(sample_data)
    predictions, probabilities = predictor.predict(sample_df)
    
    print(f"\nSample Prediction:")
    print(f"  Predicted Flare Class: {predictions[0]}")
    print(f"  Confidence: {np.max(probabilities[0]):.3f}")
    print(f"  All Probabilities: {probabilities[0]}")