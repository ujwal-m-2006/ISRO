import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import services
from services.data_ingestion import DataIngestionService
from services.data_storage import DataStorageService
from database import get_db
from models import InstrumentStatus


class IngestionOrchestrator:
    def __init__(self):
        self.ingestion_service = DataIngestionService()
        self.storage_service = DataStorageService()
    
    async def run_complete_ingestion_cycle(self) -> Dict[str, Any]:
        """
        Run complete ingestion cycle: scrape -> parse -> validate -> store
        """
        logger.info("Starting complete ingestion cycle")
        
        # Get database session
        db = next(get_db())
        
        try:
            # Step 1: Ingest data from PRADAN
            ingestion_result = await self.ingestion_service.run_ingestion_cycle()
            
            if not ingestion_result:
                logger.error("Ingestion cycle failed")
                return {"status": "failed", "error": "Ingestion cycle failed"}
            
            # Step 2: Store SoLEXS data
            solexs_data = ingestion_result.get("solexs")
            if solexs_data and solexs_data.get("validation", {}).get("is_valid"):
                stored_solexs = self.storage_service.store_solexs_observation(db, solexs_data)
                if stored_solexs:
                    logger.info(f"Successfully stored SoLEXS observation ID {stored_solexs.id}")
                    # Update instrument status
                    self.storage_service.update_instrument_status(
                        db, 
                        "SoLEXS", 
                        "online", 
                        health_score=0.95,
                        details={"last_ingestion": datetime.now().isoformat()}
                    )
                else:
                    logger.warning("Failed to store SoLEXS observation")
            
            # Step 3: Store HEL1OS data
            hel1os_data = ingestion_result.get("hel1os")
            if hel1os_data and hel1os_data.get("validation", {}).get("is_valid"):
                stored_hel1os = self.storage_service.store_hel1os_observation(db, hel1os_data)
                if stored_hel1os:
                    logger.info(f"Successfully stored HEL1OS observation ID {stored_hel1os.id}")
                    # Update instrument status
                    self.storage_service.update_instrument_status(
                        db, 
                        "HEL1OS", 
                        "online", 
                        health_score=0.92,
                        details={"last_ingestion": datetime.now().isoformat()}
                    )
                else:
                    logger.warning("Failed to store HEL1OS observation")
            
            # Step 4: Return result
            result = {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "ingestion_result": ingestion_result,
                "stored_solexs_id": getattr(stored_solexs, 'id', None) if 'stored_solexs' in locals() else None,
                "stored_hel1os_id": getattr(stored_hel1os, 'id', None) if 'stored_hel1os' in locals() else None
            }
            
            logger.info("Complete ingestion cycle completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error in complete ingestion cycle: {e}")
            return {"status": "failed", "error": str(e)}
        finally:
            db.close()
    
    async def start_continuous_ingestion(self, interval_minutes: int = 60):
        """
        Start continuous ingestion with specified interval
        """
        logger.info(f"Starting continuous ingestion every {interval_minutes} minutes")
        
        while True:
            try:
                result = await self.run_complete_ingestion_cycle()
                
                if result["status"] == "success":
                    logger.info(f"Ingestion cycle completed successfully at {result['timestamp']}")
                else:
                    logger.error(f"Ingestion cycle failed: {result.get('error', 'Unknown error')}")
                
                # Wait for next interval
                await asyncio.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("Continuous ingestion stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in continuous ingestion loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

# Example usage
if __name__ == "__main__":
    orchestrator = IngestionOrchestrator()
    
    # For testing, run a single cycle
    import asyncio
    result = asyncio.run(orchestrator.run_complete_ingestion_cycle())
    print(f"Ingestion result: {result}")