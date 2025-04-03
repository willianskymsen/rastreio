# modules/database.py
import time
import logging
import mysql.connector
import cx_Oracle
from typing import Optional, Union
from .config import MYSQL_CONFIG, ORACLE_PASSWORD, ORACLE_TNS_ALIAS, ORACLE_USER

logger = logging.getLogger(__name__)

# Variáveis para controle de inicialização
_mysql_initialized = False
_oracle_initialized = False

# Tipo personalizado para conexões
DBConnection = Union[mysql.connector.MySQLConnection, cx_Oracle.Connection]

def init_databases():
    """Inicializa e testa todas as conexões com bancos de dados"""
    init_mysql()
    init_oracle()

def init_mysql():
    """Inicializa e testa a conexão com MySQL"""
    global _mysql_initialized

    if _mysql_initialized:
        return

    logger.info("🔧 Verificando conexão com MySQL...")

    try:
        connection = mysql.connector.connect(
            **MYSQL_CONFIG, 
            autocommit=False, 
            connect_timeout=5
        )

        if connection.is_connected():
            close_connection(connection)
            logger.info("✅ Conexão com MySQL estabelecida!")
            _mysql_initialized = True  # Definir como inicializado apenas se a conexão for bem-sucedida
        else:
            logger.error("❌ Falha na conexão com MySQL!")
            raise RuntimeError("Não foi possível conectar ao MySQL")

    except mysql.connector.Error as e:
        logger.error(f"Erro ao conectar ao MySQL: {str(e)}")
        raise RuntimeError(f"Não foi possível conectar ao MySQL: {str(e)}")

def init_oracle():
    """Inicializa e testa a conexão com Oracle"""
    global _oracle_initialized
    
    if _oracle_initialized:
        return

    logger.info("🔧 Verificando conexão com Oracle...")
    conn = get_oracle_connection()
    if conn:
        close_connection(conn)
        logger.info("✅ Conexão com Oracle estabelecida!")
        _oracle_initialized = True
    else:
        logger.error("❌ Falha na conexão com Oracle!")
        raise RuntimeError("Não foi possível conectar ao Oracle")

def get_mysql_connection(max_retries: int = 3, retry_delay: int = 1) -> Optional[mysql.connector.MySQLConnection]:
    """Estabelece conexão com MySQL com retry automático"""
    
    for attempt in range(max_retries):
        try:
            connection = mysql.connector.connect(
                **MYSQL_CONFIG, 
                autocommit=False, 
                connect_timeout=5
            )
            if connection.is_connected():
                logger.info(f"✅ Conexão MySQL estabelecida (tentativa {attempt + 1}/{max_retries})")
                return connection
        except mysql.connector.Error as e:
            logger.error(f"⚠️ Tentativa {attempt + 1} falhou: {str(e)}")
            if attempt == max_retries - 1:
                logger.critical("❌ Falha ao conectar ao MySQL após várias tentativas")
                raise RuntimeError(f"Erro crítico: não foi possível conectar ao MySQL após {max_retries} tentativas. Último erro: {str(e)}")
            time.sleep(retry_delay)
    
    return None

def get_oracle_connection() -> Optional[cx_Oracle.Connection]:
    """Estabelece conexão com Oracle Database"""
    try:
        connection = cx_Oracle.connect(
            user=ORACLE_USER,
            password=ORACLE_PASSWORD,
            dsn=ORACLE_TNS_ALIAS
        )
        with connection.cursor() as cursor:
            cursor.execute("ALTER SESSION SET CURRENT_SCHEMA = FOCCO3I")

        logger.info("Conexão Oracle estabelecida")
        return connection
    except cx_Oracle.Error as e:
        logger.error(f"Erro ao conectar ao Oracle: {str(e)}")
    except Exception as e:
        logger.error(f"Erro inesperado ao conectar ao Oracle: {str(e)}")
    
    return None

def close_connection(connection: Optional[DBConnection]):
    """Fecha uma conexão de banco de dados de forma segura"""
    if not connection:
        return
    
    try:
        if isinstance(connection, mysql.connector.MySQLConnection) and connection.is_connected():
            connection.close()
            logger.debug("Conexão MySQL fechada com sucesso")
        elif isinstance(connection, cx_Oracle.Connection) and connection:
            connection.close()
            logger.debug("Conexão Oracle fechada com sucesso")
    except cx_Oracle.DatabaseError as e:
        logger.warning(f"Erro ao fechar conexão Oracle: {str(e)}")
    except mysql.connector.Error as e:
        logger.warning(f"Erro ao fechar conexão MySQL: {str(e)}")
    except Exception as e:
        logger.error(f"Erro inesperado ao fechar conexão: {str(e)}")

# Teste as conexões se o arquivo for executado diretamente
if __name__ == "__main__":
    print("Testando conexões com bancos de dados...")
    
    # Teste MySQL
    mysql_conn = get_mysql_connection()
    if mysql_conn:
        print("✅ Conexão MySQL OK")
        close_connection(mysql_conn)
    else:
        print("❌ Falha na conexão MySQL")
    
    # Teste Oracle
    oracle_conn = get_oracle_connection()
    if oracle_conn:
        print("✅ Conexão Oracle OK")
        close_connection(oracle_conn)
    else:
        print("⚠️ Conexão Oracle não configurada ou falhou")