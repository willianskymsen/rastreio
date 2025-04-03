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
import schedule

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
        _config['max_retries'] = max_retries
    logger.info(f"Módulo de tasks inicializado com configuração: {_config}")

def processar_nfe(cursor, chave_nfe: str, num_nf: str, transportadora: str, cidade: str, uf: str, dt_saida: str) -> bool:
    """
    Processa NF-e alimentando as tabelas do banco de dados.
    """
    try:
        dados_api = fetch_tracking_data(chave_nfe)

        if not dados_api or dados_api.get("status") != "SUCESSO":
            logger.warning(f"NF-e {num_nf} não encontrada na API")
            cursor.execute("""
                UPDATE nfe_status
                SET status = 'NAO_ENCONTRADO', updated_at = NOW()
                WHERE chave_nfe = %s
            """, (chave_nfe,))
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

def _should_process_with_current_system(conn, transportadora_descricao):
    local_cursor = conn.cursor(buffered=True)  # Usa um cursor buffered
    try:
        local_cursor.execute("SELECT SISTEMA FROM transportadoras WHERE DESCRICAO = %s", (transportadora_descricao,))
        transportadora_data = local_cursor.fetchone()
        local_cursor.fetchall()  # Garante que todos os resultados foram consumidos
        return transportadora_data and transportadora_data[0] == 1
    except mysql.connector.Error as e:
        logger.error(f"Erro ao verificar sistema da transportadora '{transportadora_descricao}': {e}")
        return False
    finally:
        local_cursor.close()

def process_pending_nfes():
    """Processa NF-es com status PENDENTE."""
    logger.info("Verificando e processando NF-es com status PENDENTE.")
    conn = get_mysql_connection()
    if not conn:
        logger.error("Falha ao obter conexão com o banco de dados para verificar NF-es PENDENTES.")
        return
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT chave_nfe, NUM_NF, transportadora, cidade, uf, dt_saida
                FROM nfe_status
                WHERE status = 'PENDENTE'
            """)
            pending_nfes = cursor.fetchall()
            for nfe in pending_nfes:
                chave_nfe, num_nf, transportadora, cidade, uf, dt_saida_str = nfe
                if _should_process_with_current_system(conn, transportadora):
                    logger.info(f"Processando NF-e {num_nf} (PENDENTE) - Transportadora '{transportadora}'.")
                    processar_nfe(cursor, chave_nfe, num_nf, transportadora, cidade, uf, str(dt_saida_str))
                    conn.commit()
                else:
                    logger.info(f"Ignorando NF-e {num_nf} (PENDENTE) - Transportadora '{transportadora}' usa outro sistema.")
    finally:
        close_connection(conn)
    logger.info("Verificação e processamento de NF-es com status PENDENTE concluído.")

def process_transit_nfes():
    """Processa NF-es com status EM_TRANSITO."""
    logger.info("Verificando e processando NF-es com status EM_TRANSITO.")
    conn = get_mysql_connection()
    if not conn:
        logger.error("Falha ao obter conexão com o banco de dados para verificar NF-es EM_TRANSITO.")
        return
    try:
        with conn.cursor() as cursor:
            now = datetime.now()
            cursor.execute("""
                SELECT chave_nfe, NUM_NF, transportadora, cidade, uf, dt_saida, last_processed_at
                FROM nfe_status
                WHERE status = 'EM_TRANSITO' AND (last_processed_at IS NULL OR last_processed_at < %s)
            """, (now - timedelta(hours=3),))
            transit_nfes = cursor.fetchall()
            for nfe in transit_nfes:
                chave_nfe, num_nf, transportadora, cidade, uf, dt_saida_str, last_processed_at = nfe
                if _should_process_with_current_system(conn, transportadora):
                    logger.info(f"Processando NF-e {num_nf} (EM_TRANSITO) - Transportadora '{transportadora}'.")
                    processar_nfe(cursor, chave_nfe, num_nf, transportadora, cidade, uf, str(dt_saida_str))
                    conn.commit()
                else:
                    logger.info(f"Ignorando NF-e {num_nf} (EM_TRANSITO) - Transportadora '{transportadora}' usa outro sistema.")
    finally:
        close_connection(conn)
    logger.info("Verificação e processamento de NF-es com status EM_TRANSITO concluído.")

def process_not_found_nfes():
    """Processa NF-es com status NAO_ENCONTRADO."""
    logger.info("Verificando e processando NF-es com status NAO_ENCONTRADO.")
    conn = get_mysql_connection()
    if not conn:
        logger.error("Falha ao obter conexão com o banco de dados para verificar NF-es NAO_ENCONTRADO.")
        return
    try:
        with conn.cursor() as cursor:
            now = datetime.now()
            cursor.execute("""
                SELECT chave_nfe, NUM_NF, transportadora, cidade, uf, dt_saida, last_processed_at
                FROM nfe_status
                WHERE status = 'NAO_ENCONTRADO' AND (last_processed_at IS NULL OR last_processed_at < %s)
            """, (now - timedelta(hours=10),))
            not_found_nfes = cursor.fetchall()
            for nfe in not_found_nfes:
                chave_nfe, num_nf, transportadora, cidade, uf, dt_saida_str, last_processed_at = nfe
                if _should_process_with_current_system(conn, transportadora):
                    logger.info(f"Processando NF-e {num_nf} (NAO_ENCONTRADO) - Transportadora '{transportadora}'.")
                    processar_nfe(cursor, chave_nfe, num_nf, transportadora, cidade, uf, str(dt_saida_str))
                    conn.commit()
                else:
                    logger.info(f"Ignorando NF-e {num_nf} (NAO_ENCONTRADO) - Transportadora '{transportadora}' usa outro sistema.")
    finally:
        close_connection(conn)
    logger.info("Verificação e processamento de NF-es com status NAO_ENCONTRADO concluído.")

def run_scheduler():
    """Executa o agendador de tarefas."""
    schedule.every(11).minutes.do(process_pending_nfes)
    schedule.every(5).hours.do(process_transit_nfes)
    schedule.every(10).hours.do(process_not_found_nfes)

    while True:
        schedule.run_pending()
        time.sleep(1)

def start_background_process():
    """Inicia o agendamento de tarefas em um processo separado."""
    logger.info("Iniciando o agendamento de tarefas...")
    # Executa a verificação de PENDENTE uma vez na inicialização
    process_pending_nfes()
    logger.info("Verificação inicial de NF-es PENDENTES concluída.")

    process = Process(target=run_scheduler, daemon=True)
    process.start()
    logger.info("Agendador de tarefas iniciado em background.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    init_tasks()
    start_background_process()
    while True:
        time.sleep(1)