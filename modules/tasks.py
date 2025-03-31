# modules/tasks.py
import logging
from typing import Optional
import mysql.connector
from modules.database import get_mysql_connection, close_mysql_connection
from modules.tracking import fetch_tracking_data
from modules.status import determinar_status

logger = logging.getLogger(__name__)

# Configurações do módulo
_config = {
    'max_retries': 3,
    'default_status': 'EM_TRANSITO',
    'log_all_events': True
}

def init_tasks(max_retries: Optional[int] = None, 
               log_all_events: Optional[bool] = None):
    """
    Inicializa o módulo de tasks com configurações personalizadas
    
    Args:
        max_retries: Número máximo de tentativas para operações (opcional)
        log_all_events: Se deve registrar todos os eventos ou apenas o último (opcional)
    """
    if max_retries is not None:
        _config['max_retries'] = max_retries
    if log_all_events is not None:
        _config['log_all_events'] = log_all_events
    
    logger.info(f"Módulo de tasks inicializado com configuração: {_config}")

def processar_nfe(chave_nfe: str, 
                 num_nf: str, 
                 transportadora: str, 
                 cidade: str, 
                 uf: str, 
                 dt_saida: str) -> bool:
    """
    Processa NF-e alimentando as tabelas do banco de dados.
    
    Args:
        chave_nfe: Chave de acesso da NF-e
        num_nf: Número da nota fiscal
        transportadora: Nome da transportadora
        cidade: Cidade de destino
        uf: UF de destino
        dt_saida: Data de saída no formato string
        
    Returns:
        bool: True se o processamento foi bem-sucedido, False caso contrário
    """
    conn = None
    try:
        # Tentativa de obter dados da API
        dados_api = fetch_tracking_data(chave_nfe)
        conn = get_mysql_connection()
        if not conn:
            logger.error("Falha ao obter conexão com o banco de dados")
            return False

        cursor = conn.cursor()
        
        # Caso não encontre dados na API
        if not dados_api or dados_api.get("status") != "SUCESSO":
            logger.warning(f"NF-e {num_nf} não encontrada na API")
            _insert_default_status(
                cursor, chave_nfe, num_nf, transportadora, cidade, uf, dt_saida
            )
            conn.commit()
            return True

        # Processa os eventos encontrados
        items = dados_api["dados"]["items"]
        status = determinar_status(items)
        
        if _config['log_all_events']:
            for evento in items:
                _insert_evento(
                    cursor, chave_nfe, num_nf, evento, status, 
                    transportadora, cidade, uf
                )
        else:
            # Insere apenas o último evento se log_all_events for False
            _insert_evento(
                cursor, chave_nfe, num_nf, items[-1], status,
                transportadora, cidade, uf
            )

        conn.commit()
        logger.info(f"NF-e {num_nf} processada com sucesso. Status: {status}")
        return True

    except Exception as e:
        logger.error(f"Erro ao processar NF-e {num_nf}: {str(e)}", exc_info=True)
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            close_mysql_connection(conn)

def _insert_evento(cursor, chave_nfe, num_nf, evento, status, transportadora, cidade, uf):
    """Função auxiliar para inserir um evento no banco"""
    try:
        cursor.execute(
            """
            INSERT INTO nfe_logs 
            (chave_nfe, NUM_NF, evento, data_hora, status, transportadora, cidade, uf)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                evento = VALUES(evento),
                status = VALUES(status)
            """,
            (chave_nfe, num_nf, evento["ocorrencia"], evento["data_hora"], 
             status, transportadora, cidade, uf)
        )
    except mysql.connector.Error as e:
        logger.warning(f"Evento já existe para NF-e {num_nf}, atualizando dados: {str(e)}")

def _insert_default_status(cursor, chave_nfe, num_nf, transportadora, cidade, uf, dt_saida):
    """Função auxiliar para inserir status padrão quando não encontra dados"""
    cursor.execute(
        """
        INSERT INTO nfe_status 
        (chave_nfe, NUM_NF, ultimo_evento, data_hora, status, transportadora, cidade, uf)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (chave_nfe, num_nf, "CONSULTA_REALIZADA", dt_saida, 
         "NAO_ENCONTRADO", transportadora, cidade, uf)
    )