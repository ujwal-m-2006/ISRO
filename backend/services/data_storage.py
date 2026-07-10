import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import models
from ..models import SoLEXSObservation, HEL1OSObservation, InstrumentStatus


class DataStorageService:
    def __init__(self):
        pass
    
    def store_solexs_observation(self, db: Session, data: Dict[str, Any]) -> Optional[SoLEXSObservation]:
        """
        Store SoLEXS observation in database
        """
        try:
            # Create database model instance
            observation = SoLEXSObservation(
                timestamp=data.get("timestamp", datetime.now()),
                soft_xray_flux=data.get("soft_xray_flux"),
                energy_spectrum=data.get("energy_spectrum"),
                photon_count=data.get("photon_count"),
                temperature=data.get("temperature"),
                observation_time=data.get("observation_time"),
                detector_health=data.get("detector_health"),
                quality_flag=data.get("quality_flag", "good"),
                instrument_status=data.get("instrument_status", "operational"),
                source=data.get("source", "PRADAN")
            )
            
            # Add to database
            db.add(observation)
            db.commit()
            db.refresh(observation)
            
            logger.info(f"Stored SoLEXS observation with ID {observation.id}")
            return observation
            
        except Exception as e:
            logger.error(f"Error storing SoLEXS observation: {e}")
            db.rollback()
            return None
    
    def store_hel1os_observation(self, db: Session, data: Dict[str, Any]) -> Optional[HEL1OSObservation]:
        """
        Store HEL1OS observation in database
        """
        try:
            # Create database model instance
            observation = HEL1OSObservation(
                timestamp=data.get("timestamp", datetime.now()),
                hard_xray_flux=data.get("hard_xray_flux"),
                energy_distribution=data.get("energy_distribution"),
                detector_count=data.get("detector_count"),
                peak_energy=data.get("peak_energy"),
                observation_time=data.get("observation_time"),
                detector_health=data.get("detector_health"),
                quality_flag=data.get("quality_flag", "good"),
                instrument_status=data.get("instrument_status", "operational"),
                source=data.get("source", "PRADAN")
            )
            
            # Add to database
            db.add(observation)
            db.commit()
            db.refresh(observation)
            
            logger.info(f"Stored HEL1OS observation with ID {observation.id}")
            return observation
            
        except Exception as e:
            logger.error(f"Error storing HEL1OS observation: {e}")
            db.rollback()
            return None
    
    def update_instrument_status(self, db: Session, instrument_name: str, status: str, health_score: float = None, details: dict = None):
        """
        Update instrument status in database
        """
        try:
            # Check if instrument status already exists
            existing_status = db.query(InstrumentStatus).filter(
                InstrumentStatus.instrument_name == instrument_name
            ).first()
            
            if existing_status:
                # Update existing record
                existing_status.status = status
                existing_status.last_updated = datetime.now()
                if health_score is not None:
                    existing_status.health_score = health_score
                if details is not None:
                    existing_status.details = details
            else:
                # Create new record
                new_status = InstrumentStatus(
                    instrument_name=instrument_name,
                    status=status,
                    last_updated=datetime.now(),
                    health_score=health_score,
                    details=details
                )
                db.add(new_status)
            
            db.commit()
            logger.info(f"Updated {instrument_name} status to {status}")
            
        except Exception as e:
            logger.error(f"Error updating {instrument_name} status: {e}")
            db.rollback()

# Example usage
if __name__ == "__main__":
    # This would be called from the ingestion service
    # storage_service = DataStorageService()
    # storage_service.store_solexs_observation(db, parsed_data)
    pass