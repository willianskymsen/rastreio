# modules/xml_parser.py
import logging
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional
from modules.status import determinar_status

logger = logging.getLogger(__name__)

# Module configuration
_config = {
    'max_xml_log_length': 500,
    'strict_parsing': False,
    'default_status': 'SEM_EVENTOS'
}

def init_xml_parser(max_xml_log_length: Optional[int] = None,
                   strict_parsing: Optional[bool] = None,
                   default_status: Optional[str] = None):
    """
    Initialize XML parser module with custom configuration
    
    Args:
        max_xml_log_length: Max characters to log from XML (for debugging)
        strict_parsing: Whether to fail on minor XML issues
        default_status: Default status when no events are found
    """
    if max_xml_log_length is not None:
        _config['max_xml_log_length'] = max_xml_log_length
    if strict_parsing is not None:
        _config['strict_parsing'] = strict_parsing
    if default_status is not None:
        _config['default_status'] = default_status
        
    logger.info("XML parser initialized with config: %s", _config)

def parse_xml(xml_data: str) -> Dict[str, Any]:
    """
    Process tracking XML and return formatted data
    
    Args:
        xml_data: Raw XML string from API
        
    Returns:
        Dictionary containing:
        - status: Processing status
        - status_entrega: Delivery status
        - dados: Processed data
        - mensagem: Status message
        - items: List of tracking events
    """
    try:
        logger.debug("Iniciando parse do XML (first %d chars): %s...",
                    _config['max_xml_log_length'],
                    xml_data[:_config['max_xml_log_length']])
        
        root = ET.fromstring(xml_data)
        
        # Check API success status
        success = root.find(".//success")
        if success is None or success.text.lower() != "true":
            message = root.find(".//message")
            return {
                "status": "NAO_ENCONTRADO",
                "mensagem": message.text if message is not None else "Documento não encontrado",
                "items": []
            }

        # Process document
        documento = root.find(".//documento")
        if documento is None:
            return {
                "status": "ERRO_PROCESSAMENTO",
                "mensagem": "XML inválido - tag 'documento' não encontrada",
                "items": []
            }

        # Extract header data
        header = documento.find("header")
        header_data = {
            "remetente": _safe_extract_text(header, "remetente"),
            "destinatario": _safe_extract_text(header, "destinatario"),
            "nro_nf": _safe_extract_text(header, "nro_nf"),
            "pedido": _safe_extract_text(header, "pedido")
        }

        # Process tracking events
        items = _process_items(documento.findall(".//item"))
        status_entrega = determinar_status(items) if items else _config['default_status']

        return {
            "status": "SUCESSO",
            "status_entrega": status_entrega,
            "dados": {
                **header_data,
                "items": items
            },
            "mensagem": "Documento processado com sucesso"
        }

    except ET.ParseError as e:
        logger.error("Erro ao fazer parse do XML: %s", str(e))
        return {
            "status": "ERRO_PROCESSAMENTO",
            "mensagem": f"Erro no XML: {str(e)}",
            "items": []
        }
    except Exception as e:
        logger.error("Erro inesperado ao processar XML: %s", str(e))
        return {
            "status": "ERRO_PROCESSAMENTO",
            "mensagem": f"Erro inesperado: {str(e)}",
            "items": []
        }

def _safe_extract_text(element: Optional[ET.Element], tag: str) -> str:
    """Helper to safely extract text from XML elements"""
    if element is None:
        return ""
    target = element.find(tag)
    return target.text if target is not None else ""

def _process_items(items: List[ET.Element]) -> List[Dict[str, str]]:
    """Process list of item elements into tracking events"""
    return [
        {
            "data_hora": _safe_extract_text(item, "data_hora"),
            "ocorrencia": _safe_extract_text(item, "ocorrencia"),
            "descricao": _safe_extract_text(item, "descricao")
        }
        for item in items
    ]