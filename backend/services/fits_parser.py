import astropy.io.fits as fits
import numpy as np
from datetime import datetime
import pytz
from typing import Dict, Any, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FITSParser:
    def __init__(self):
        pass
    
    def parse_solexs_fits(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Parse SoLEXS FITS file and extract relevant solar flare data
        """
        try:
            # Open FITS file
            hdul = fits.open(file_path)
            
            # Extract header information
            header = hdul[0].header if len(hdul) > 0 else {}
            
            # Extract data
            data = hdul[0].data if len(hdul) > 0 and hdul[0].data is not None else None
            
            # Parse SoLEXS specific data
            result = {
                "timestamp": self._extract_timestamp(header),
                "soft_xray_flux": self._extract_soft_xray_flux(data, header),
                "energy_spectrum": self._extract_energy_spectrum(data, header),
                "photon_count": self._extract_photon_count(data, header),
                "temperature": self._extract_temperature(header),
                "observation_time": self._extract_observation_time(header),
                "detector_health": self._extract_detector_health(header),
                "quality_flag": self._extract_quality_flag(header),
                "instrument_status": self._extract_instrument_status(header),
                "source": "PRADAN",
                "file_path": file_path
            }
            
            hdul.close()
            return result
            
        except Exception as e:
            logger.error(f"Error parsing SoLEXS FITS file {file_path}: {e}")
            return None
    
    def parse_hel1os_fits(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Parse HEL1OS FITS file and extract relevant solar flare data
        """
        try:
            # Open FITS file
            hdul = fits.open(file_path)
            
            # Extract header information
            header = hdul[0].header if len(hdul) > 0 else {}
            
            # Extract data
            data = hdul[0].data if len(hdul) > 0 and hdul[0].data is not None else None
            
            # Parse HEL1OS specific data
            result = {
                "timestamp": self._extract_timestamp(header),
                "hard_xray_flux": self._extract_hard_xray_flux(data, header),
                "energy_distribution": self._extract_energy_distribution(data, header),
                "detector_count": self._extract_detector_count(data, header),
                "peak_energy": self._extract_peak_energy(header),
                "observation_time": self._extract_observation_time(header),
                "detector_health": self._extract_detector_health(header),
                "quality_flag": self._extract_quality_flag(header),
                "instrument_status": self._extract_instrument_status(header),
                "source": "PRADAN",
                "file_path": file_path
            }
            
            hdul.close()
            return result
            
        except Exception as e:
            logger.error(f"Error parsing HEL1OS FITS file {file_path}: {e}")
            return None
    
    def _extract_timestamp(self, header) -> datetime:
        """
        Extract timestamp from FITS header
        """
        # Try common FITS timestamp keywords
        for keyword in ['DATE-OBS', 'DATE', 'TIME-OBS', 'UTSTART']:
            if keyword in header:
                try:
                    # Handle different timestamp formats
                    timestamp_str = str(header[keyword])
                    # Remove any trailing spaces or comments
                    timestamp_str = timestamp_str.split()[0]
                    # Try to parse as ISO format
                    return datetime.fromisoformat(timestamp_str.replace('T', ' ').replace('/', '-'))
                except ValueError:
                    pass
        
        # Default to current time if no timestamp found
        return datetime.now(pytz.UTC)
    
    def _extract_soft_xray_flux(self, data, header) -> Optional[float]:
        """
        Extract soft X-ray flux from SoLEXS data
        """
        # SoLEXS measures in 2-22 keV range
        if data is not None:
            # Simple example - actual implementation would depend on FITS structure
            return float(np.mean(data)) if data.size > 0 else None
        return None
    
    def _extract_hard_xray_flux(self, data, header) -> Optional[float]:
        """
        Extract hard X-ray flux from HEL1OS data
        """
        # HEL1OS measures in 10-150 keV range
        if data is not None:
            # Simple example - actual implementation would depend on FITS structure
            return float(np.mean(data)) if data.size > 0 else None
        return None
    
    def _extract_energy_spectrum(self, data, header) -> Optional[list]:
        """
        Extract energy spectrum from SoLEXS data
        """
        if data is not None:
            # Convert to list for JSON serialization
            return data.tolist() if hasattr(data, 'tolist') else [float(x) for x in data.flatten()[:100]]
        return None
    
    def _extract_energy_distribution(self, data, header) -> Optional[list]:
        """
        Extract energy distribution from HEL1OS data
        """
        if data is not None:
            # Convert to list for JSON serialization
            return data.tolist() if hasattr(data, 'tolist') else [float(x) for x in data.flatten()[:100]]
        return None
    
    def _extract_photon_count(self, data, header) -> Optional[int]:
        """
        Extract photon count from SoLEXS data
        """
        if data is not None:
            return int(np.sum(data)) if data.size > 0 else 0
        return 0
    
    def _extract_detector_count(self, data, header) -> Optional[int]:
        """
        Extract detector count from HEL1OS data
        """
        if data is not None:
            return int(np.sum(data)) if data.size > 0 else 0
        return 0
    
    def _extract_temperature(self, header) -> Optional[float]:
        """
        Extract temperature from SoLEXS header
        """
        # Look for temperature keywords
        for keyword in ['TEMPERAT', 'TEMP', 'TEFF']:
            if keyword in header:
                return float(header[keyword])
        return None
    
    def _extract_peak_energy(self, header) -> Optional[float]:
        """
        Extract peak energy from HEL1OS header
        """
        # Look for peak energy keywords
        for keyword in ['PEAK_ENE', 'PEAK', 'ENERGY_PEAK']:
            if keyword in header:
                return float(header[keyword])
        return None
    
    def _extract_observation_time(self, header) -> Optional[datetime]:
        """
        Extract observation time from header
        """
        return self._extract_timestamp(header)
    
    def _extract_detector_health(self, header) -> Optional[str]:
        """
        Extract detector health status from header
        """
        # Look for health keywords
        for keyword in ['HEALTH', 'STATUS', 'QUALITY']:
            if keyword in header:
                return str(header[keyword])
        return "unknown"
    
    def _extract_quality_flag(self, header) -> Optional[str]:
        """
        Extract quality flag from header
        """
        # Look for quality keywords
        for keyword in ['QUALITY', 'FLAG', 'QUAL']:
            if keyword in header:
                return str(header[keyword]).lower()
        return "good"
    
    def _extract_instrument_status(self, header) -> Optional[str]:
        """
        Extract instrument status from header
        """
        # Look for status keywords
        for keyword in ['STATUS', 'INSTRUME', 'INSTRUMENT']:
            if keyword in header:
                return str(header[keyword])
        return "operational"

# Example usage
if __name__ == "__main__":
    parser = FITSParser()
    # This would be called with actual FITS file paths
    # result = parser.parse_solexs_fits("/path/to/solexs_file.fits")
    # print(result)