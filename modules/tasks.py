# modules/tasks.py
import logging
from typing import Optional
import mysql.connector
from datetime import datetime, timedelta
from multiprocessing import Process
from modules.database import get_mysql_connection, close_connection
from modules.tracking import fetch_tracking_data
from modules.status import determinar_status, init_status
from modules import nfe_tracking_logger
import time
import schedule
import base64
import uuid

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

def _gerar_token_base64():
    """Gera um token único e o codifica em base64."""
    return base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('ascii').rstrip('=')

def gerar_e_salvar_token_nfe(cursor, num_nf: str):
    """
    Gera um token base64 para a NF e o salva no banco de dados.
    """
    try:
        token = _gerar_token_base64()
        cursor.execute(
            "INSERT INTO nfe_tokens (NUM_NF, token) VALUES (%s, %s)",
            (num_nf, token)
        )
        logger.info(f"Token gerado e salvo para a NF {num_nf}: {token}")
        return True
    except mysql.connector.IntegrityError:
        logger.info(f"Token já existe para a NF {num_nf}. Ignorando.")
        return True
    except mysql.connector.Error as e:
        logger.error(f"Erro ao gerar e salvar token para a NF {num_nf}: {e}")
        return False

def processar_nfe(cursor, chave_nfe: str, num_nf: str, transportadora: str, cidade: str, uf: str, dt_saida: str) -> bool:
    """
    Processa NF-e alimentando as tabelas do banco de dados.
    Na primeira consulta bem-sucedida, salva todos os eventos.
    Em consultas subsequentes, ignora se o status for ENTREGUE.
    """
    conn = None
    try:
        dados_api = fetch_tracking_data(chave_nfe)

        if not dados_api or dados_api.get("status") != "SUCESSO":
            logger.warning(f"NF-e {num_nf} não encontrada na API")
            cursor.execute("""
                UPDATE nfe_status
                SET status = 'NAO_ENCONTRADO', updated_at = NOW()
                WHERE chave_nfe = %s
            """, (chave_nfe,))
            nfe_tracking_logger._update_last_processed(cursor, chave_nfe)
            return True

        items = dados_api["dados"]["items"]
        ultimo_evento_api = items[-1] if items else None
        codigo_ocorrencia = ultimo_evento_api.get("codigo_ocorrencia") if ultimo_evento_api else None
        tipo_ocorrencia = ultimo_evento_api.get("ocorrencia", "").strip() if ultimo_evento_api else None

        conn = get_mysql_connection()
        if not conn:
            logger.error("Falha ao obter conexão com o banco de dados para determinar o status.")
            status = _config['default_status']
        else:
            init_status(conn)
            status = determinar_status(conn, codigo_ocorrencia)
            close_connection(conn)
            conn = None

        ultimo_codigo_ocorrencia_api = dados_api.get("ultimo_codigo_ocorrencia")
        ultimo_codigo_ocorrencia_salvar = ultimo_codigo_ocorrencia_api

        logger.info(f"NF-e {num_nf}: Último código de ocorrência da API: {ultimo_codigo_ocorrencia_api}")

        if ultimo_codigo_ocorrencia_api == '01':
            ultimo_codigo_ocorrencia_salvar = '01'
            logger.info(f"NF-e {num_nf}: Forçando último código de ocorrência para '01'.")

        # Check if events have been logged before
        cursor.execute("SELECT COUNT(*) FROM nfe_logs WHERE chave_nfe = %s", (chave_nfe,))
        eventos_ja_logados = cursor.fetchone()[0]

        if not eventos_ja_logados:
            # First time logging events
            logger.info(f"NF-e {num_nf}: Primeira consulta bem-sucedida. Logando todos os eventos.")
            for evento in items:
                nfe_tracking_logger.insert_evento(cursor, chave_nfe, num_nf, evento, status, transportadora, cidade, uf)
            # Chamando a função para gerar e salvar o token
            gerar_e_salvar_token_nfe(cursor, num_nf)
        else:
            # Subsequent checks
            if status == 'ENTREGUE':
                logger.info(f"NF-e {num_nf}: Status ENTREGUE em consulta subsequente. Ignorando eventos.")
                cursor.execute("SELECT status FROM nfe_status WHERE chave_nfe = %s", (chave_nfe,))
                current_status = cursor.fetchone()[0]
                if current_status != 'ENTREGUE':
                    nfe_tracking_logger._update_nfe_status(cursor, chave_nfe, status, ultimo_codigo_ocorrencia_salvar, tipo_ocorrencia)
                    logger.info(f"NF-e {num_nf}: Atualizando status para ENTREGUE.")
                return True
            else:
                logger.info(f"NF-e {num_nf}: Consulta subsequente. Logando apenas o último evento.")
                nfe_tracking_logger.insert_evento(cursor, chave_nfe, num_nf, items[-1], status, transportadora, cidade, uf)

        nfe_tracking_logger._update_nfe_status(cursor, chave_nfe, status, ultimo_codigo_ocorrencia_salvar, tipo_ocorrencia)
        logger.info(f"NF-e {num_nf} processada com sucesso. Status: {status}, Último Evento: {ultimo_codigo_ocorrencia_salvar}")
        return True

    except Exception as e:
        logger.error(f"Erro ao processar NF-e {num_nf}: {str(e)}", exc_info=True)
        return False
    finally:
        if conn:
            close_connection(conn)

def _should_process_with_current_system(conn, transportadora_descricao):
    local_cursor = conn.cursor(buffered=True)
    try:
        local_cursor.execute("SELECT SISTEMA FROM transportadoras WHERE DESCRICAO = %s", (transportadora_descricao,))
        transportadora_data = local_cursor.fetchone()
        local_cursor.fetchall()
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