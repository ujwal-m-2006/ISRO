import requests
from bs4 import BeautifulSoup
import os
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re

from services.pradan_auth import login, PradanAuthError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PRADANScraper:
    def __init__(self):
        self.base_url = "https://pradan1.issdc.gov.in/al1/"
        self.authenticated = False
        self.auth_error: Optional[str] = None
        try:
            self.session = login()
            self.authenticated = True
        except PradanAuthError as e:
            self.auth_error = str(e)
            logger.warning("PRADAN authentication unavailable: %s", e)
            self.session = requests.Session()
            self.session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            })

    def get_payload_page(self, payload_name: str) -> Optional[str]:
        """
        Get the HTML content of a specific payload's data browser (requires an
        authenticated session — returns None if login failed/unavailable).

        Real PRADAN structure (confirmed by inspecting the live authenticated
        page): the /protected/payload.xhtml page is just a menu of payload
        cards; each links to /protected/browse.xhtml?id=<payload>, which
        server-renders a PrimeFaces <p:dataTable> of the actual data products
        (no AJAX needed for the first page of results).
        """
        if not self.authenticated:
            logger.warning("Skipping %s fetch — PRADAN not authenticated (%s)", payload_name, self.auth_error)
            return None
        try:
            url = f"{self.base_url}protected/browse.xhtml?id={payload_name.lower()}"
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Error fetching {payload_name} page: {e}")
            return None

    _ISO_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
    _SIZE_RE = re.compile(r"^\d+\.\d+$")  # real sizes are always decimals (e.g. 6796.066); the "#" row-index column is a plain int

    def parse_fits_files(self, html_content: str, instrument: str) -> List[Dict[str, str]]:
        """
        Parse the PRADAN data-products table (id="tableForm:lazyDocTable_data")
        into a list of downloadable products. These are ZIP archives (e.g.
        AL1_SLX_L1_20260630_v1.0.zip) containing the actual FITS files — not
        raw .fits links directly on this page.

        Column layout varies per instrument (e.g. HEL1OS has an extra
        "Preview" thumbnail column SoLEXS doesn't), so cells are matched by
        content pattern (the /downloadData/ link, ISO-timestamp cells, a
        numeric size cell) rather than fixed indices.
        """
        if not html_content:
            return []

        soup = BeautifulSoup(html_content, "html.parser")
        table_body = soup.find("tbody", id="tableForm:lazyDocTable_data")
        if not table_body:
            return []

        files = []
        for row in table_body.find_all("tr", recursive=False):
            cells = row.find_all("td", recursive=False)
            download_link = None
            for cell in cells:
                a = cell.find("a", href=True)
                if not a or "/downloadData/" not in a["href"]:
                    continue
                path = a["href"].lower().split("?")[0]
                if path.endswith((".zip", ".fits", ".fit")):
                    download_link = a
                    break
            if not download_link:
                continue

            times = [c.get_text(strip=True) for c in cells if self._ISO_TIME_RE.match(c.get_text(strip=True))]
            sizes = [c.get_text(strip=True) for c in cells if self._SIZE_RE.match(c.get_text(strip=True))]
            href = download_link["href"]

            files.append(
                {
                    "url": href if href.startswith("http") else f"https://pradan1.issdc.gov.in{href}",
                    "filename": download_link.get_text(strip=True) or os.path.basename(href.split("?")[0]),
                    "instrument": instrument,
                    "start_time": times[0] if len(times) > 0 else None,
                    "end_time": times[1] if len(times) > 1 else None,
                    "size_kb": sizes[0] if sizes else None,
                }
            )
        return files
    
    def download_fits_file(self, file_info: Dict[str, str], download_dir: str = "./downloads") -> Optional[str]:
        """
        Download a FITS file
        """
        try:
            # Create download directory if it doesn't exist
            os.makedirs(download_dir, exist_ok=True)
            
            # Download the file
            response = self.session.get(file_info['url'], timeout=300)
            response.raise_for_status()
            
            # Save the file
            filepath = os.path.join(download_dir, file_info['filename'])
            with open(filepath, 'wb') as f:
                f.write(response.content)
            
            logger.info(f"Downloaded {file_info['filename']} to {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Error downloading {file_info['filename']}: {e}")
            return None
    
    def get_latest_solexs_data(self) -> List[Dict[str, str]]:
        """
        Get latest SoLEXS FITS files
        """
        html_content = self.get_payload_page("SoLEXS")
        return self.parse_fits_files(html_content, "SoLEXS")
    
    def get_latest_hel1os_data(self) -> List[Dict[str, str]]:
        """
        Get latest HEL1OS FITS files
        """
        html_content = self.get_payload_page("HEL1OS")
        return self.parse_fits_files(html_content, "HEL1OS")
    
    def monitor_and_download(self, interval_minutes: int = 60):
        """
        Monitor PRADAN portal and download new data
        """
        logger.info(f"Starting PRADAN monitoring every {interval_minutes} minutes")
        
        while True:
            try:
                # Get latest data for both instruments
                solexs_files = self.get_latest_solexs_data()
                hel1os_files = self.get_latest_hel1os_data()
                
                logger.info(f"Found {len(solexs_files)} SoLEXS files and {len(hel1os_files)} HEL1OS files")
                
                # Download new files
                for file_info in solexs_files[:5]:  # Limit to first 5 for testing
                    self.download_fits_file(file_info)
                
                for file_info in hel1os_files[:5]:  # Limit to first 5 for testing
                    self.download_fits_file(file_info)
                
                # Wait for next interval
                time.sleep(interval_minutes * 60)
                
            except KeyboardInterrupt:
                logger.info("Monitoring stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)  # Wait 1 minute before retrying

# Example usage
if __name__ == "__main__":
    scraper = PRADANScraper()
    # For testing, just get latest files
    solexs_files = scraper.get_latest_solexs_data()
    hel1os_files = scraper.get_latest_hel1os_data()
    
    print(f"SoLEXS files: {len(solexs_files)}")
    print(f"HEL1OS files: {len(hel1os_files)}")