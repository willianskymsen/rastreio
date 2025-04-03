# modules/database.py
"""
Este módulo fornece funcionalidades para estabelecer e gerenciar conexões
com bancos de dados MySQL e Oracle.

Ele inclui funções para inicializar as conexões, obter novas conexões
com tratamento de retries para MySQL, e fechar as conexões de forma segura.

As configurações para os bancos de dados são carregadas a partir do módulo
de configuração (config.py). O módulo também utiliza logging para registrar
informações sobre o status das conexões e quaisquer erros que ocorram.

Funcionalidades principais:
- Inicialização de conexões MySQL e Oracle.
- Teste de conectividade durante a inicialização.
- Obtenção de conexões MySQL com retry automático.
- Obtenção de conexões Oracle.
- Fechamento seguro de conexões para ambos os tipos de banco de dados.
- test_connections(): Testa as conexões com MySQL e/ou Oracle, conforme especificado.

Uso:
Para utilizar este módulo, importe-o e chame a função `init_databases()`
no início da sua aplicação para garantir que as conexões com os bancos
de dados estejam estabelecidas e funcionando. A função `test_connections()`
pode ser usada para verificar a conectividade com bancos de dados específicos
através de argumentos de linha de comando (-m para MySQL, -o para Oracle).
Para ver a ajuda detalhada sobre o módulo, use o argumento -H ou --module-help.
"""
import time
import logging
import mysql.connector
import cx_Oracle
from typing import Optional, Union
from .config import MYSQL_CONFIG, ORACLE_PASSWORD, ORACLE_TNS_ALIAS, ORACLE_USER
import argparse
import sys

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
    connection = None
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
    finally:
        if connection:
            pass
    return connection

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

def help_database_module():
    """Exibe informações de ajuda sobre o módulo database."""
    import inspect
    from . import database  # Importa o módulo

    print("=" * 40)
    print(f"Ajuda para o módulo: {database.__name__}")
    print("=" * 40)
    print(inspect.getdoc(database) or "Nenhuma documentação disponível para o módulo.")
    print("\n")

    print("-" * 40)
    print("Funções Principais:")
    print("-" * 40)

    module_functions = [
        database.init_databases,
        database.init_mysql,
        database.init_oracle,
        database.get_mysql_connection,
        database.get_oracle_connection,
        database.close_connection,
        database.test_connections, # Adicionando a nova função à lista de ajuda
    ]

    for func in module_functions:
        print(f"\nFunção: {func.__name__}")
        docstring = inspect.getdoc(func)
        if docstring:
            print(docstring)
        else:
            print("Nenhuma documentação disponível para esta função.")

    print("\n")
    print("-" * 40)
    print("Observações:")
    print("-" * 40)
    print("- Este módulo fornece funcionalidades para conectar e gerenciar bancos de dados MySQL e Oracle.")
    print("- As configurações de conexão são carregadas do módulo 'config'.")
    print("- Utilize a função 'init_databases()' para inicializar as conexões.")
    print("- Utilize 'get_mysql_connection()' e 'get_oracle_connection()' para obter conexões.")
    print("- Não se esqueça de fechar as conexões utilizando 'close_connection()'.")
    print("- A função 'test_connections()' permite testar a conectividade com bancos de dados específicos.")
    print("=" * 40)

def test_connections(test_mysql: bool = True, test_oracle: bool = True):
    """
    Testa as conexões com os bancos de dados MySQL e/ou Oracle.

    Args:
        test_mysql (bool, optional): Se True, a conexão com o MySQL será testada.
                                     O padrão é True.
        test_oracle (bool, optional): Se True, a conexão com o Oracle será testada.
                                      O padrão é True.

    Uso:
        Para testar ambos os bancos de dados (comportamento padrão):
        >>> python -m modules.database

        Para testar apenas a conexão MySQL:
        >>> python -m modules.database -m

        Para testar apenas a conexão Oracle:
        >>> python -m modules.database -o

        Para ver a ajuda detalhada sobre o módulo:
        >>> python -m modules.database -H

        Você também pode usar as formas longas dos argumentos:
        >>> python -m modules.database --mysql
        >>> python -m modules.database --oracle
        >>> python -m modules.database --module-help
    """
    print("Iniciando teste de conexões...")

    if test_mysql:
        print("\nTestando conexão MySQL...")
        mysql_conn = get_mysql_connection()
        if mysql_conn:
            print("✅ Conexão MySQL OK")
            close_connection(mysql_conn)
        else:
            print("❌ Falha na conexão MySQL")

    if test_oracle:
        print("\nTestando conexão Oracle...")
        oracle_conn = get_oracle_connection()
        if oracle_conn:
            print("✅ Conexão Oracle OK")
            close_connection(oracle_conn)
        else:
            print("⚠️ Conexão Oracle não configurada ou falhou")

    print("\nTeste de conexões concluído.")

class CustomHelpFormatter(argparse.HelpFormatter):
    def _format_actions_usage(self, actions, groups):
        usage = super()._format_actions_usage(actions, groups)
        return usage.replace('options', 'opções')

    def format_help(self):
        help_string = super().format_help()
        return help_string.replace('options', 'opções')

# Teste as conexões se o arquivo for executado diretamente
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Testar conexões de banco de dados.",
                                     formatter_class=CustomHelpFormatter,
                                     add_help=False)
    parser.add_argument("-m", "--mysql", action="store_true", help="Testar conexão MySQL.")
    parser.add_argument("-o", "--oracle", action="store_true", help="Testar conexão Oracle.")
    parser.add_argument("-h", "--module-help", action="store_true", help="Mostrar ajuda detalhada sobre o módulo de banco de dados.")

    args = parser.parse_args()

    if args.module_help:
        help_database_module()
        sys.exit(0)

    test_mysql_flag = args.mysql
    test_oracle_flag = args.oracle

    if not test_mysql_flag and not test_oracle_flag:
        test_mysql_flag = True
        test_oracle_flag = True

    print("\nTestando conexões ao executar o módulo...")
    test_connections(test_mysql=test_mysql_flag, test_oracle=test_oracle_flag)