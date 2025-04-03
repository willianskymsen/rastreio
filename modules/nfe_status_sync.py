# modules/nfe_status_sync.py
import logging
from modules.database import get_mysql_connection, close_connection
import mysql.connector
import time
import threading

logger = logging.getLogger(__name__)

_running = True
NFE_STATUS_SYNC_INTERVAL_SECONDS = 600  # Executa a sincronização a cada 10 minutos (600 segundos)

def stop_sync():
    """Sets the flag to stop the synchronization loop."""
    global _running
    _running = False

def sync_nfe_to_nfe_status_periodically():
    """
    Verifica periodicamente se existem NUM_NF na tabela nfe que não estão na tabela nfe_status
    e importa os dados necessários para a tabela nfe_status.
    """
    while _running:
        conn = None
        cursor = None
        try:
            conn = get_mysql_connection()
            if not conn:
                logger.error("Falha ao obter conexão com o banco de dados MySQL.")
                time.sleep(NFE_STATUS_SYNC_INTERVAL_SECONDS)
                continue

            cursor = conn.cursor()

            # Buscar todos os NUM_NF da tabela nfe
            cursor.execute("SELECT NUM_NF FROM nfe")
            nfe_nums = {row[0] for row in cursor.fetchall()}

            # Buscar todos os NUM_NF da tabela nfe_status
            cursor.execute("SELECT NUM_NF FROM nfe_status")
            nfe_status_nums = {row[0] for row in cursor.fetchall()}

            # Identificar os NUM_NF que estão em nfe mas não em nfe_status
            novas_nfs = nfe_nums - nfe_status_nums

            if novas_nfs:
                logger.info(f"Encontradas {len(novas_nfs)} novas NF-es na tabela nfe para adicionar à nfe_status.")
                insert_query = """
                        INSERT INTO nfe_status (chave_nfe, NUM_NF, ultimo_evento, data_hora, status, transportadora, cidade, uf, dt_saida)
                        SELECT n.CHAVE_ACESSO_NFEL, n.NUM_NF, '', NOW(), 'PENDENTE', n.NOME_TRP, n.CIDADE, n.UF, n.DT_SAIDA
                        FROM nfe n
                        WHERE n.NUM_NF = %s
                          AND NOT EXISTS (SELECT 1 FROM nfe_status ns WHERE ns.chave_nfe = n.CHAVE_ACESSO_NFEL)
                    """
                for num_nf in novas_nfs:
                    try:
                        cursor.execute(insert_query, (num_nf,))
                    except mysql.connector.Error as err:
                        logger.error(f"Erro ao inserir dados da NF {num_nf} na nfe_status: {err}")
                conn.commit()
                logger.info("Novas NF-es importadas para a tabela nfe_status com status 'PENDENTE'.")
            else:
                logger.info("Não foram encontradas novas NF-es na tabela nfe para sincronizar com nfe_status.")

        except mysql.connector.Error as error:
            logger.error(f"Erro ao sincronizar nfe com nfe_status: {error}")
        finally:
            if cursor:
                cursor.close()
            if conn:
                close_connection(conn)

        time.sleep(NFE_STATUS_SYNC_INTERVAL_SECONDS)

if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # This will run the sync only once if called directly
    sync_nfe_to_nfe_status_periodically()