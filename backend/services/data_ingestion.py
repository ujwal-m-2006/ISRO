import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import services
from .pradan_scraper import PRADANScraper
from .fits_parser import FITSParser
from .data_validator import DataValidator


class DataIngestionService:
    def __init__(self):
        self.scraper = PRADANScraper()
        self.parser = FITSParser()
        self.validator = DataValidator()
    
    async def ingest_solexs_data(self) -> Optional[Dict[str, Any]]:
        """
        Ingest SoLEXS data from PRADAN portal
        """
        try:
            # Step 1: Get latest SoLEXS files from PRADAN
            solexs_files = self.scraper.get_latest_solexs_data()
            
            if not solexs_files:
                logger.warning("No SoLEXS files found")
                return None
            
            # Step 2: Download and parse first file (for demo)
            file_info = solexs_files[0]
            downloaded_path = self.scraper.download_fits_file(file_info)
            
            if not downloaded_path:
                logger.error("Failed to download SoLEXS file")
                return None
            
            # Step 3: Parse FITS file
            parsed_data = self.parser.parse_solexs_fits(downloaded_path)
            
            if not parsed_data:
                logger.error("Failed to parse SoLEXS FITS file")
                return None
            
            # Step 4: Validate data
            validation_result = self.validator.validate_solexs_data(parsed_data)
            
            # Add validation results to parsed data
            parsed_data["validation"] = validation_result
            
            logger.info(f"Successfully ingested SoLEXS data: {parsed_data['timestamp']}")
            return parsed_data
            
        except Exception as e:
            logger.error(f"Error ingesting SoLEXS data: {e}")
            return None
    
    async def ingest_hel1os_data(self) -> Optional[Dict[str, Any]]:
        """
        Ingest HEL1OS data from PRADAN portal
        """
        try:
            # Step 1: Get latest HEL1OS files from PRADAN
            hel1os_files = self.scraper.get_latest_hel1os_data()
            
            if not hel1os_files:
                logger.warning("No HEL1OS files found")
                return None
            
            # Step 2: Download and parse first file (for demo)
            file_info = hel1os_files[0]
            downloaded_path = self.scraper.download_fits_file(file_info)
            
            if not downloaded_path:
                logger.error("Failed to download HEL1OS file")
                return None
            
            # Step 3: Parse FITS file
            parsed_data = self.parser.parse_hel1os_fits(downloaded_path)
            
            if not parsed_data:
                logger.error("Failed to parse HEL1OS FITS file")
                return None
            
            # Step 4: Validate data
            validation_result = self.validator.validate_hel1os_data(parsed_data)
            
            # Add validation results to parsed data
            parsed_data["validation"] = validation_result
            
            logger.info(f"Successfully ingested HEL1OS data: {parsed_data['timestamp']}")
            return parsed_data
            
        except Exception as e:
            logger.error(f"Error ingesting HEL1OS data: {e}")
            return None
    
    async def run_ingestion_cycle(self):
        """
        Run a complete ingestion cycle for both instruments
        """
        logger.info("Starting data ingestion cycle")
        
        # Ingest SoLEXS data
        solexs_data = await self.ingest_solexs_data()
        
        # Ingest HEL1OS data
        hel1os_data = await self.ingest_hel1os_data()
        
        # Return combined result
        result = {
            "timestamp": datetime.now().isoformat(),
            "solexs": solexs_data,
            "hel1os": hel1os_data,
            "status": "completed"
        }
        
        logger.info("Data ingestion cycle completed")
        return result

# Example usage
if __name__ == "__main__":
    ingestion_service = DataIngestionService()
    
    # For testing, run a single cycle
    import asyncio
    result = asyncio.run(ingestion_service.run_ingestion_cycle())
    print(f"Ingestion result: {result}")