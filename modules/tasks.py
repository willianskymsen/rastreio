import logging
from typing import Optional
import mysql.connector
from datetime import datetime, timedelta
from multiprocessing import Process
from modules.database import get_mysql_connection, close_connection
from modules.tracking import fetch_tracking_data
from modules.status import determinar_status
from modules.nfe_tracking_logger import insert_evento, insert_default_status
import time

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
    """
    if max_retries is not None:
        _config['max_retries'] = max_retries
    if log_all_events is not None:
        _config['log_all_events'] = log_all_events
    logger.info(f"Módulo de tasks inicializado com configuração: {_config}")

def processar_nfe(cursor, chave_nfe: str, num_nf: str, transportadora: str, cidade: str, uf: str, dt_saida: str) -> bool:
    """
    Processa NF-e alimentando as tabelas do banco de dados.
    """
    try:
        dados_api = fetch_tracking_data(chave_nfe)

        if not dados_api or dados_api.get("status") != "SUCESSO":
            logger.warning(f"NF-e {num_nf} não encontrada na API")
            insert_default_status(cursor, chave_nfe, num_nf, transportadora, cidade, uf, dt_saida, "")
            _update_last_processed(cursor, chave_nfe)
            return True

        items = dados_api["dados"]["items"]
        status = determinar_status(items)
        ultimo_codigo_ocorrencia = dados_api.get("ultimo_codigo_ocorrencia")

        if _config['log_all_events']:
            for evento in items:
                insert_evento(cursor, chave_nfe, num_nf, evento, status, transportadora, cidade, uf)
        else:
            insert_evento(cursor, chave_nfe, num_nf, items[-1], status, transportadora, cidade, uf)

        _update_nfe_status(cursor, chave_nfe, status, ultimo_codigo_ocorrencia)
        logger.info(f"NF-e {num_nf} processada com sucesso. Status: {status}, Último Evento: {ultimo_codigo_ocorrencia}")
        return True

    except Exception as e:
        logger.error(f"Erro ao processar NF-e {num_nf}: {str(e)}", exc_info=True)
        return False

def check_and_process_nfes():
    """
    Consulta a tabela nfe_status e envia as chaves para processamento
    """
    conn = None
    try:
        conn = get_mysql_connection()
        if not conn:
            logger.error("Falha ao obter conexão com o banco de dados para verificar NF-es")
            return

        with conn.cursor(buffered=True) as cursor:
            cursor.execute("""
                SELECT chave_nfe, NUM_NF, status, transportadora, cidade, uf, dt_saida, last_processed_at
                FROM nfe_status
                WHERE status IN ('PENDENTE', 'EM_TRANSITO', 'NAO_ENCONTRADO')
            """)
            nfes = cursor.fetchall()

            now = datetime.now()
            for nfe in nfes:
                chave_nfe, num_nf, status, transportadora, cidade, uf, dt_saida_str, last_processed_at = nfe
                dt_saida = dt_saida_str if isinstance(dt_saida_str, datetime) else datetime.strptime(dt_saida_str, '%Y-%m-%d %H:%M:%S') if dt_saida_str else None
                time_difference = now - (last_processed_at or dt_saida or datetime.min)

                if _should_process_with_current_system(cursor, transportadora):
                    if status == 'PENDENTE' or \
                       (status == 'EM_TRANSITO' and time_difference >= timedelta(hours=3)) or \
                       (status == 'NAO_ENCONTRADO' and time_difference >= timedelta(hours=10)):
                        processar_nfe(cursor, chave_nfe, num_nf, transportadora, cidade, uf, dt_saida_str)

            conn.commit() # Commit all changes at the end of processing all NF-es

    except Exception as e:
        logger.error(f"Erro ao verificar e processar NF-es: {e}", exc_info=True)
        if conn:
            conn.rollback()
    finally:
        if conn:
            close_connection(conn)

def _update_last_processed(cursor, chave_nfe):
    try:
        cursor.execute("""
            UPDATE nfe_status
            SET last_processed_at = NOW()
            WHERE chave_nfe = %s
        """, (chave_nfe,))
    except mysql.connector.Error as e:
        logger.error(f"Erro ao atualizar last_processed_at para {chave_nfe}: {e}")

def _update_nfe_status(cursor, chave_nfe, status, ultimo_codigo_ocorrencia):
    try:
        cursor.execute("""
            UPDATE nfe_status
            SET status = %s, ultimo_evento = %s, updated_at = NOW()
            WHERE chave_nfe = %s
        """, (status, ultimo_codigo_ocorrencia, chave_nfe))
    except mysql.connector.Error as e:
        logger.error(f"Erro ao atualizar nfe_status para {chave_nfe}: {e}")

def _should_process_with_current_system(cursor, transportadora_descricao):
    try:
        cursor.execute("SELECT SISTEMA FROM transportadoras WHERE DESCRICAO = %s", (transportadora_descricao,))
        transportadora_data = cursor.fetchone()
        return transportadora_data and transportadora_data[0] == 1
    except mysql.connector.Error as e:
        logger.error(f"Erro ao verificar sistema da transportadora '{transportadora_descricao}': {e}")
        return False

def run_scheduled_tasks():
    while True:
        check_and_process_nfes()
        time.sleep(11 * 60)

def start_background_process():
    """Inicia a verificação de NF-es em um processo separado"""
    process = Process(target=run_scheduled_tasks, daemon=True)
    process.start()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    init_tasks()
    start_background_process()