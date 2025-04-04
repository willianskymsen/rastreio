# modules/json_parser.py
import logging
from typing import Dict, List, Any, Optional
from modules.status import determinar_status, init_status  # Import init_status as well
from modules.database import get_mysql_connection, close_connection
import re

logger = logging.getLogger(__name__)

# Module configuration
_config = {
    'max_json_log_length': 500,
    'strict_parsing': False,
    'default_status': 'SEM_EVENTOS'
}

def init_json_parser(max_json_log_length: Optional[int] = None,
                     strict_parsing: Optional[bool] = None,
                     default_status: Optional[str] = None):
    """
    Initialize JSON parser module with custom configuration

    Args:
        max_json_log_length: Max characters to log from JSON (for debugging)
        strict_parsing: Whether to fail on minor JSON issues
        default_status: Default status when no events are found
    """
    if max_json_log_length is not None:
        _config['max_json_log_length'] = max_json_log_length
    if strict_parsing is not None:
        _config['strict_parsing'] = strict_parsing
    if default_status is not None:
        _config['default_status'] = default_status

    logger.info("JSON parser initialized with config: %s", _config)

def parse_json(json_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process tracking JSON and return formatted data

    Args:
        json_data: Raw JSON dict from API

    Returns:
        Dictionary containing:
        - status: Processing status
        - status_entrega: Delivery status
        - dados: Processed data
        - mensagem: Status message
        - items: List of tracking events
    """
    conn = None
    try:
        logger.debug("Iniciando parse do JSON (first %d chars): %s...",
                     _config['max_json_log_length'],
                     str(json_data)[:_config['max_json_log_length']])

        # Check API success status
        if not json_data.get('success', False):
            return {
                "status": "NAO_ENCONTRADO",
                "mensagem": json_data.get('message', 'Documento não encontrado'),
                "items": []
            }

        # Process document
        documento = json_data.get('documento')
        if documento is None:
            return {
                "status": "ERRO_PROCESSAMENTO",
                "mensagem": "JSON inválido - campo 'documento' não encontrado",
                "items": []
            }

        # Extract header data
        header = documento.get('header', {})
        header_data = {
            "remetente": header.get('remetente', ''),
            "destinatario": header.get('destinatario', ''),
            "nro_nf": header.get('nro_nf', ''),
            "pedido": header.get('pedido', '')
        }

        # Process tracking events
        tracking_items = documento.get('tracking', [])
        items = _process_items(tracking_items)

        conn = get_mysql_connection()
        if not conn:
            logger.error("Falha ao obter conexão com o banco de dados para determinar o status.")
            status_entrega = _config['default_status']
        else:
            init_status(conn)  # Ensure status module is initialized
            if items:
                ultimo_evento = items[-1]
                codigo_ocorrencia = ultimo_evento.get("codigo_ocorrencia")
                status_entrega = determinar_status(conn, codigo_ocorrencia)
            else:
                status_entrega = _config['default_status']

        return {
            "status": "SUCESSO",
            "status_entrega": status_entrega,
            "dados": {
                **header_data,
                "items": items
            },
            "mensagem": json_data.get('message', 'Documento processado com sucesso')
        }

    except Exception as e:
        logger.error("Erro inesperado ao processar JSON: %s", str(e))
        return {
            "status": "ERRO_PROCESSAMENTO",
            "mensagem": f"Erro inesperado: {str(e)}",
            "items": []
        }
    finally:
        if conn:
            close_connection(conn)

def _process_items(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Processa eventos de rastreamento extraindo TODOS os campos."""
    processed_items = []
    for item in items:
        # Separa descrição e código da ocorrência (tentativa inicial)
        ocorrencia = item.get("ocorrencia", "")
        descricao_ocorrencia = ocorrencia
        codigo_ocorrencia = ""

        codigo_ocorrencia_match = re.search(r'\((\d+)\)$', ocorrencia)
        if codigo_ocorrencia_match:
            descricao_ocorrencia = ocorrencia[:codigo_ocorrencia_match.start()].strip()
            codigo_ocorrencia = codigo_ocorrencia_match.group(1)

        processed_item = {
            "data_hora": item.get("data_hora", ""),
            "dominio": item.get("dominio", ""),
            "filial": item.get("filial", ""),
            "cidade": item.get("cidade", ""),
            "ocorrencia": descricao_ocorrencia,  # Descrição sem o código (se encontrado)
            "codigo_ocorrencia": codigo_ocorrencia,  # Código (se encontrado)
            "descricao": item.get("descricao", ""),
            "tipo": item.get("tipo", ""),
            "data_hora_efetiva": item.get("data_hora_efetiva", ""),
            "nome_recebedor": item.get("nome_recebedor", ""),
            "nro_doc_recebedor": item.get("nro_doc_recebedor", "")
        }
        processed_items.append(processed_item)

    return processed_items

# Teste interativo (mantenha para testes locais)
if __name__ == "__main__":
    import json

    init_json_parser()
    print("🔍 Teste do JSON Parser (Ctrl+C para sair)")
    print("----------------------------------------")

    while True:
        try:
            json_str = input("\nCole o JSON completo ou deixe em branco para exemplo: ").strip()

            if not json_str:
                json_str = '''{
                    "success": true,
                    "message": "Documento localizado com sucesso",
                    "documento": {
                        "header": {
                            "remetente": "Exemplo Remetente",
                            "destinatario": "Exemplo Destinatário",
                            "nro_nf": "12345"
                        },
                        "tracking": [
                            {
                                "data_hora": "2025-01-01T12:00:00",
                                "ocorrencia": "Evento exemplo (123)",
                                "descricao": "Descrição exemplo"
                            },
                            {
                                "data_hora": "2025-01-02T14:00:00",
                                "ocorrencia": "Outro evento sem código",
                                "descricao": "Descrição detalhada do outro evento"
                            }
                        ]
                    }
                }'''

            data = json.loads(json_str)
            resultado = parse_json(data)

            print("\n📄 Resultado:")
            print("-------------")
            print(f"Status: {resultado.get('status')}")
            print(f"Mensagem: {resultado.get('mensagem')}")

            if "dados" in resultado:
                print("\n📦 Dados:")
                for k, v in resultado["dados"].items():
                    if k != "items":
                        print(f"- {k}: {v}")

                print("\n🔄 Eventos:")
                for i, item in enumerate(resultado["dados"]["items"], 1):
                    print(f"{i}. {item['data_hora']} - {item['ocorrencia']} ({item.get('codigo_ocorrencia', '')})")
                    print(f"  {item['descricao']}")

        except json.JSONDecodeError:
            print("❌ JSON inválido!")
        except KeyboardInterrupt:
            print("\nSaindo...")
            break
        except Exception as e:
            print(f"❌ Erro: {str(e)}")