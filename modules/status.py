# modules/status.py
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Variável para controle de inicialização
_initialized = False

# Configurações padrão dos padrões de status
PADROES_ENTREGUE = {
    "MERCADORIA ENTREGUE",
    "ENTREGA REALIZADA",
    "ENTREGUE AO DESTINATÁRIO",
    "CONCLUÍDO"
}

PADROES_PROBLEMA = {
    "PROBLEMA",
    "DEVOLVIDO",
    "EXTRAVIADO",
    "ROUBADO",
    "AVARIA",
    "CANCELADO"
}

def init_status(padroes_entregue: Optional[set] = None, 
                padroes_problema: Optional[set] = None):
    """
    Inicializa o módulo de status com configurações personalizadas
    
    Args:
        padroes_entregue: Conjunto de padrões para status ENTREGUE (opcional)
        padroes_problema: Conjunto de padrões para status PROBLEMA (opcional)
    """
    global _initialized, PADROES_ENTREGUE, PADROES_PROBLEMA
    
    if _initialized:
        return

    if padroes_entregue:
        PADROES_ENTREGUE = padroes_entregue
    if padroes_problema:
        PADROES_PROBLEMA = padroes_problema

    logger.info("Módulo de status inicializado")
    logger.debug(f"Padrões ENTREGUE: {PADROES_ENTREGUE}")
    logger.debug(f"Padrões PROBLEMA: {PADROES_PROBLEMA}")
    
    _initialized = True

def determinar_status(eventos: List[Dict]) -> str:
    """
    Determina o status da NF-e com base nos eventos retornados pela API.
    
    Args:
        eventos: Lista de dicionários contendo informações de eventos de rastreio
        
    Returns:
        str: Status da NF-e, que pode ser:
            - "ENTREGUE" (quando há confirmação de entrega)
            - "PROBLEMA" (quando há ocorrências de problemas ou devolução)
            - "EM_TRANSITO" (quando está a caminho sem problemas)
            - "NAO_ENCONTRADO" (quando não há eventos)
    """
    if not eventos:
        return "NAO_ENCONTRADO"

    for evento in eventos:
        ocorrencia = evento.get("ocorrencia", "").upper()
        
        if any(padrao in ocorrencia for padrao in PADROES_ENTREGUE):
            return "ENTREGUE"
            
        if any(padrao in ocorrencia for padrao in PADROES_PROBLEMA):
            return "PROBLEMA"

    return "EM_TRANSITO"