# modules/tracking.py
import logging
import requests
from typing import Optional, Dict, Any
from modules.xml_parser import parse_xml

logger = logging.getLogger(__name__)

# Configuration defaults
_config = {
    'api_url': "https://ssw.inf.br/api/trackingdanfe",
    'timeout': 10,
    'headers': {"Content-Type": "application/x-www-form-urlencoded"}
}

def init_tracking(api_url: Optional[str] = None, 
                 timeout: Optional[int] = None,
                 headers: Optional[Dict[str, str]] = None):
    """
    Initialize tracking module with custom configuration
    
    Args:
        api_url: Custom API endpoint URL
        timeout: Request timeout in seconds
        headers: Custom request headers
    """
    if api_url:
        _config['api_url'] = api_url
    if timeout:
        _config['timeout'] = timeout
    if headers:
        _config['headers'] = headers
        
    logger.info("Tracking module initialized with config: %s", {
        'api_url': _config['api_url'],
        'timeout': _config['timeout']
    })

def fetch_tracking_data(chave_nfe: str) -> Optional[Dict[str, Any]]:
    """
    Fetch tracking data from API based on NF-e key
    
    Args:
        chave_nfe: NF-e access key
        
    Returns:
        Parsed tracking data or None if request fails
    """
    data = {"chave_nfe": chave_nfe}
    
    try:
        response = requests.post(
            _config['api_url'],
            data=data,
            headers=_config['headers'],
            timeout=_config['timeout']
        )
        response.raise_for_status()
        logger.debug("API response received for NF-e %s", chave_nfe)
        return parse_xml(response.text)
        
    except requests.exceptions.RequestException as e:
        logger.error("API request failed for NF-e %s: %s", chave_nfe, str(e))
        return None
    except Exception as e:
        logger.error("Unexpected error processing NF-e %s: %s", chave_nfe, str(e))
        return None