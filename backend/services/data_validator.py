import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataValidator:
    def __init__(self):
        pass
    
    def validate_solexs_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate SoLEXS data and add quality indicators
        """
        validation_result = {
            "is_valid": True,
            "quality_flag": "good",
            "issues": [],
            "timestamp_validation": "valid",
            "detector_health_validation": "valid",
            "data_completeness": "complete"
        }
        
        # Check timestamp validity
        if "timestamp" in data and data["timestamp"]:
            now = datetime.now()
            # Check if timestamp is within reasonable range (not in future or too old)
            if data["timestamp"] > now + timedelta(hours=1):
                validation_result["is_valid"] = False
                validation_result["quality_flag"] = "warning"
                validation_result["issues"].append("Timestamp is in the future")
                validation_result["timestamp_validation"] = "invalid"
            elif data["timestamp"] < now - timedelta(days=30):
                validation_result["quality_flag"] = "warning"
                validation_result["issues"].append("Timestamp is older than 30 days")
                validation_result["timestamp_validation"] = "old"
        else:
            validation_result["is_valid"] = False
            validation_result["quality_flag"] = "bad"
            validation_result["issues"].append("Missing timestamp")
            validation_result["timestamp_validation"] = "missing"
        
        # Check detector health
        if "detector_health" in data and data["detector_health"]:
            health_status = str(data["detector_health"]).lower()
            if "error" in health_status or "fault" in health_status or "offline" in health_status:
                validation_result["is_valid"] = False
                validation_result["quality_flag"] = "bad"
                validation_result["issues"].append(f"Detector health issue: {data['detector_health']}")
                validation_result["detector_health_validation"] = "error"
            elif "warning" in health_status or "degraded" in health_status:
                validation_result["quality_flag"] = "warning"
                validation_result["issues"].append(f"Detector health warning: {data['detector_health']}")
                validation_result["detector_health_validation"] = "warning"
        else:
            validation_result["quality_flag"] = "warning"
            validation_result["issues"].append("Missing detector health information")
            validation_result["detector_health_validation"] = "missing"
        
        # Check data completeness
        required_fields = ["soft_xray_flux", "energy_spectrum", "photon_count"]
        missing_fields = []
        for field in required_fields:
            if field not in data or data[field] is None:
                missing_fields.append(field)
        
        if missing_fields:
            validation_result["quality_flag"] = "warning"
            validation_result["issues"].append(f"Missing required fields: {missing_fields}")
            validation_result["data_completeness"] = "incomplete"
        
        # Add validation metadata
        validation_result["validated_at"] = datetime.now().isoformat()
        validation_result["data_id"] = data.get("file_path", "unknown")
        
        return validation_result
    
    def validate_hel1os_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate HEL1OS data and add quality indicators
        """
        validation_result = {
            "is_valid": True,
            "quality_flag": "good",
            "issues": [],
            "timestamp_validation": "valid",
            "detector_health_validation": "valid",
            "data_completeness": "complete"
        }
        
        # Check timestamp validity
        if "timestamp" in data and data["timestamp"]:
            now = datetime.now()
            # Check if timestamp is within reasonable range (not in future or too old)
            if data["timestamp"] > now + timedelta(hours=1):
                validation_result["is_valid"] = False
                validation_result["quality_flag"] = "warning"
                validation_result["issues"].append("Timestamp is in the future")
                validation_result["timestamp_validation"] = "invalid"
            elif data["timestamp"] < now - timedelta(days=30):
                validation_result["quality_flag"] = "warning"
                validation_result["issues"].append("Timestamp is older than 30 days")
                validation_result["timestamp_validation"] = "old"
        else:
            validation_result["is_valid"] = False
            validation_result["quality_flag"] = "bad"
            validation_result["issues"].append("Missing timestamp")
            validation_result["timestamp_validation"] = "missing"
        
        # Check detector health
        if "detector_health" in data and data["detector_health"]:
            health_status = str(data["detector_health"]).lower()
            if "error" in health_status or "fault" in health_status or "offline" in health_status:
                validation_result["is_valid"] = False
                validation_result["quality_flag"] = "bad"
                validation_result["issues"].append(f"Detector health issue: {data['detector_health']}")
                validation_result["detector_health_validation"] = "error"
            elif "warning" in health_status or "degraded" in health_status:
                validation_result["quality_flag"] = "warning"
                validation_result["issues"].append(f"Detector health warning: {data['detector_health']}")
                validation_result["detector_health_validation"] = "warning"
        else:
            validation_result["quality_flag"] = "warning"
            validation_result["issues"].append("Missing detector health information")
            validation_result["detector_health_validation"] = "missing"
        
        # Check data completeness
        required_fields = ["hard_xray_flux", "energy_distribution", "detector_count"]
        missing_fields = []
        for field in required_fields:
            if field not in data or data[field] is None:
                missing_fields.append(field)
        
        if missing_fields:
            validation_result["quality_flag"] = "warning"
            validation_result["issues"].append(f"Missing required fields: {missing_fields}")
            validation_result["data_completeness"] = "incomplete"
        
        # Add validation metadata
        validation_result["validated_at"] = datetime.now().isoformat()
        validation_result["data_id"] = data.get("file_path", "unknown")
        
        return validation_result
    
    def get_quality_level(self, quality_flag: str) -> int:
        """
        Convert quality flag to numeric level for sorting/filtering
        """
        quality_levels = {
            "good": 3,
            "warning": 2,
            "bad": 1
        }
        return quality_levels.get(quality_flag.lower(), 2)

# Example usage
if __name__ == "__main__":
    validator = DataValidator()
    
    # Example SoLEXS data
    solexs_data = {
        "timestamp": datetime.now(),
        "soft_xray_flux": 1.23e-6,
        "energy_spectrum": [1.0, 2.0, 3.0],
        "photon_count": 12345,
        "detector_health": "operational"
    }
    
    result = validator.validate_solexs_data(solexs_data)
    print(f"SoLEXS validation: {result}")