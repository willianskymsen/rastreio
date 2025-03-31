import time
import logging
import mysql.connector
from config import MYSQL_CONFIG
from typing import Optional

logger = logging.getLogger(__name__)

# Variável para verificar se o banco já foi testado
_db_initialized = False

def init_db():
    """Função de inicialização que testa a conexão"""
    global _db_initialized
    if not _db_initialized:
        logger.info("🔧 Verificando conexão com o MySQL...")
        conn = get_mysql_connection()
        if conn:
            close_mysql_connection(conn)  # Usando a nova função para fechar
            logger.info("✅ Conexão com MySQL estabelecida!")
            _db_initialized = True
        else:
            logger.error("❌ Falha na conexão com MySQL!")
            raise RuntimeError("Não foi possível conectar ao banco de dados")

def get_mysql_connection(max_retries: int = 3, retry_delay: int = 1) -> Optional[mysql.connector.MySQLConnection]:
    """Estabelece conexão com o MySQL com retry automático
    
    Args:
        max_retries: Número máximo de tentativas
        retry_delay: Tempo de espera entre tentativas (em segundos)
        
    Returns:
        Objeto de conexão MySQL ou None se falhar
    """
    for attempt in range(max_retries):
        try:
            connection = mysql.connector.connect(
                **MYSQL_CONFIG, 
                autocommit=False, 
                connect_timeout=5,
                pool_size=5
            )
            if connection.is_connected():
                logger.info(f"Conexão MySQL estabelecida (tentativa {attempt + 1}/{max_retries})")
                return connection
        except mysql.connector.Error as e:
            logger.error(f"Tentativa {attempt + 1} falhou: {str(e)}")
            if attempt == max_retries - 1:
                logger.critical("Falha ao conectar ao MySQL após várias tentativas")
                return None
            time.sleep(retry_delay)
    return None

def close_mysql_connection(connection: Optional[mysql.connector.MySQLConnection]):
    """Fecha uma conexão com o MySQL de forma segura
    
    Args:
        connection: Objeto de conexão MySQL a ser fechado
    """
    if connection and connection.is_connected():
        try:
            connection.close()
            logger.debug("Conexão MySQL fechada com sucesso")
        except mysql.connector.Error as e:
            logger.error(f"Erro ao fechar conexão MySQL: {str(e)}")