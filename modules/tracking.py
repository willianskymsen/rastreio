# modules/tracking.py
import logging
import requests
from typing import Optional, Dict, Any
from modules.json_parser import parse_json

logger = logging.getLogger(__name__)

# Configurações padrão
_config = {
    'api_url': "https://ssw.inf.br/api/trackingdanfe",
    'timeout': 10,
    'headers': {"Content-Type": "application/json"}
}

def init_tracking(api_url: Optional[str] = None,
                    timeout: Optional[int] = None,
                    headers: Optional[Dict[str, str]] = None):
    """Configura o módulo para uso com JSON."""
    if api_url:
        _config['api_url'] = api_url
    if timeout:
        _config['timeout'] = timeout
    if headers:
        _config['headers'] = headers

    logger.info("Tracking module initialized with config: %s", _config)

def fetch_tracking_data(chave_nfe: str) -> Optional[Dict[str, Any]]:
    """
    Busca dados de rastreamento via API (JSON).

    Args:
        chave_nfe: Chave de acesso da NF-e (44 caracteres)

    Returns:
        Dicionário com a resposta da API ou None em caso de falha.
    """
    if not chave_nfe or len(chave_nfe) != 44:
        logger.error("Chave NF-e inválida: %s", chave_nfe)
        return None

    payload = {"chave_nfe": chave_nfe}

    try:
        response = requests.post(
            _config['api_url'],
            json=payload,
            headers=_config['headers'],
            timeout=_config['timeout']
        )
        response.raise_for_status()
        json_data = response.json()

        # Usa o json_parser para processar a resposta
        parsed_data = parse_json(json_data)
        logger.debug("API response parsed: %s", parsed_data)

        # Extrai o codigo_ocorrencia do último evento
        ultimo_codigo_ocorrencia = parsed_data['dados']['items'][-1].get("codigo_ocorrencia") if parsed_data.get('dados') and parsed_data['dados'].get('items') else None
        parsed_data['ultimo_codigo_ocorrencia'] = ultimo_codigo_ocorrencia

        return parsed_data

    except requests.exceptions.RequestException as e:
        logger.error("Falha na requisição: %s", str(e))
        return None
    except Exception as e:
        logger.error("Erro inesperado ao processar resposta: %s", str(e))
        return None

if __name__ == "__main__":
    """Modo interativo para testar o módulo isoladamente."""
    import sys
    from modules.json_parser import init_json_parser  # Importação adicional

    # Inicializa ambos os módulos
    init_tracking()
    init_json_parser()  # Inicializa o parser JSON

    print("\n🔍 Teste do Módulo de Rastreamento (JSON API)")
    print("----------------------------------------")

    # Solicita chave NF-e
    chave = input("Digite a chave NF-e (44 caracteres) ou 'sair' para cancelar: ").strip()

    if chave.lower() == 'sair':
        sys.exit(0)

    if len(chave) != 44:
        print("❌ Erro: Chave deve ter 44 caracteres!", file=sys.stderr)
        sys.exit(1)

    # Processa a consulta
    print("\n⏳ Consultando API...")
    resultado = fetch_tracking_data(chave)

    # Exibe resultados formatados
    print("\n📄 Resultado:")
    print("-------------")
    if resultado:
        print(f"Status: {resultado.get('status', 'N/A')}")
        print(f"Mensagem: {resultado.get('mensagem', 'N/A')}")
        print(f"Status Entrega: {resultado.get('status_entrega', 'N/A')}")
        print(f"Último Código de Ocorrência: {resultado.get('ultimo_codigo_ocorrencia', 'N/A')}")

        if "dados" in resultado:
            print("\n📦 Dados da NF-e:")
            for key, value in resultado["dados"].items():
                if key != "items":
                    print(f"- {key}: {value}")

            if "items" in resultado["dados"]:
                print("\n🔄 Eventos de Rastreamento:")
                for i, item in enumerate(resultado["dados"]["items"], 1):
                    print(f"{i}. {item.get('data_hora', 'N/A')}")
                    print(f"  Ocorrência: {item.get('ocorrencia', 'N/A')}")
                    print(f"  codigo_ocorrencia: {item.get('codigo_ocorrencia', 'N/A')}")
                    print(f"  Cidade: {item.get('cidade', 'N/A')}")
                    print(f"  Tipo: {item.get('tipo', 'N/A')}")
                    print(f"  Descrição: {item.get('descricao', 'N/A')}")
                    if item.get('nome_recebedor'):
                        print(f"  Recebedor: {item['nome_recebedor']} (Doc: {item.get('nro_doc_recebedor', 'N/A')})")
                    print()
    else:
        print("❌ Falha na consulta (verifique os logs)")

    print("\n----------------------------------------")