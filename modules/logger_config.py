# logger_config.py
import logging
from typing import Optional

# Variável para controle de inicialização
_initialized = False

def init_logger(config: Optional[dict] = None):
    """
    Inicializa o sistema de logging com configurações padrão ou personalizadas
    
    Args:
        config: Dicionário com configurações personalizadas (opcional)
            Exemplo: {'level': logging.DEBUG, 'filename': 'app.log'}
    """
    global _initialized
    
    if _initialized:
        return

    # Configurações padrão
    default_config = {
        'level': logging.INFO,
        'format': "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        'handlers': [
            logging.FileHandler("app.log"),
            logging.StreamHandler()
        ]
    }

    # Mescla com configurações personalizadas se fornecidas
    final_config = {**default_config, **(config or {})}

    # Aplica a configuração
    logging.basicConfig(**final_config)
    
    _initialized = True
    logging.getLogger(__name__).info("Logger configurado com sucesso")

logger = logging.getLogger(__name__)