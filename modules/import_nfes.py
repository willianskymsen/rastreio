# modules/import_nfes.py
import logging
import cx_Oracle
import mysql.connector
from modules.database import get_mysql_connection, get_oracle_connection, close_connection
from typing import Optional

logger = logging.getLogger(__name__)

# Configurações do módulo
_config = {
    'data_limite_oracle': '2025-01-01 00:00:00.000',
    'log_level': logging.INFO,  # Adicionando nível de log como configuração
    'log_format': '%(asctime)s - %(levelname)s - %(message)s', # Adicionando formato de log
    # Adicione outras configurações conforme necessário
}

def importar_nfes_oracle_mysql():
    """
    Importa dados da tabela TNFS_SAIDA do banco de dados Oracle para a tabela nfe
    do banco de dados MySQL, aplicando filtros e verificando a existência de registros
    com base na coluna NUM_NF.

    A função realiza as seguintes etapas:
    1. Estabelece conexão com os bancos de dados Oracle e MySQL utilizando as funções
       definidas no módulo `modules.database`.
    2. Executa uma query no Oracle para selecionar os dados da tabela `TNFS_SAIDA`,
       aplicando os seguintes filtros:
       - `SIT_NF = 'I'` (Situação da Nota Fiscal igual a 'I')
       - `DT_EMIS > '2025-01-01 00:00:00.000'` (Data de Emissão maior que a data limite configurada)
       - `TP_FRETE = 'C'` (Tipo do Frete igual a 'C')
    3. Para cada registro retornado do Oracle, verifica se já existe um registro com o
       mesmo valor na coluna `NUM_NF` na tabela `nfe` do MySQL.
    4. Se o registro não existir no MySQL, ele é inserido na tabela `nfe`.
    5. Registra informações sobre o número de registros encontrados, inseridos e ignorados
       (por já existirem) utilizando o logger.
    6. Em caso de erros durante a conexão com os bancos de dados ou durante a execução
       das queries, registra as informações de erro no logger.
    7. Garante o fechamento das conexões com os bancos de dados na seção `finally`.

    Raises:
        cx_Oracle.Error: Se ocorrer algum erro ao conectar ou executar query no Oracle.
        mysql.connector.Error: Se ocorrer algum erro ao conectar ou executar query no MySQL.
        Exception: Se ocorrer qualquer outro erro inesperado durante o processo.

    Returns:
        None
    """
    oracle_conn = None
    mysql_conn = None
    oracle_cursor = None
    mysql_cursor = None
    try:
        # Conectar ao banco de dados Oracle usando a função do database.py
        oracle_conn = get_oracle_connection()
        if not oracle_conn:
            logger.error("Falha ao obter conexão com o banco de dados Oracle.")
            return
        oracle_cursor = oracle_conn.cursor()
        logger.info("Conexão com o banco de dados Oracle estabelecida com sucesso.")

        # Executar a query para selecionar os dados da tabela TNFS_SAIDA com filtros
        oracle_cursor.execute("""
            SELECT NUM_NF, DT_SAIDA, CLI_ID, NOME, CNPJ_CPF_CLI, CIDADE, UF, VLR_TOTAL,
                   PESO_BRT, QTD_VOLUMES, FORN_ID, NOME_TRP, CNPJ_CPF_TRP, FORN_ID_RDP,
                   NOME_TRP_RDP, CUBAGEM, CHAVE_ACESSO_NFEL, OBS_CONF
            FROM TNFS_SAIDA
            WHERE SIT_NF = 'I'
              AND DT_EMIS > TO_TIMESTAMP(:data_limite, 'YYYY-MM-DD HH24:MI:SS.FF3')
              AND TP_FRETE = 'C'
        """, data_limite=_config['data_limite_oracle'])  # Usando a configuração
        oracle_data = oracle_cursor.fetchall()
        logger.info(f"{len(oracle_data)} registros encontrados na tabela TNFS_SAIDA do Oracle após aplicar os filtros.")

        # Conectar ao banco de dados MySQL usando a função do database.py
        mysql_conn = get_mysql_connection()
        if not mysql_conn:
            logger.error("Falha ao obter conexão com o banco de dados MySQL.")
            return

        mysql_cursor = mysql_conn.cursor()

        # Preparar a query de verificação de existência no MySQL
        check_existence_query = "SELECT COUNT(*) FROM nfe WHERE NUM_NF = %s"

        # Preparar a query de inserção para a tabela nfe do MySQL
        insert_query = """
            INSERT INTO nfe (NUM_NF, DT_SAIDA, CLI_ID, NOME, CNPJ_CPF_CLI, CIDADE, UF,
                             VLR_TOTAL, PESO_BRT, QTD_VOLUMES, FORN_ID, NOME_TRP, CNPJ_CPF_TRP,
                             FORN_ID_RDP, NOME_TRP_RDP, CUBAGEM, CHAVE_ACESSO_NFEL, OBS_CONF)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """

        # Inserir os dados no MySQL, verificando a existência previamente
        registros_inseridos = 0
        registros_existentes = 0
        for row in oracle_data:
            num_nf = row[0]  # Assumindo que NUM_NF é a primeira coluna
            mysql_cursor.execute(check_existence_query, (num_nf,))
            if mysql_cursor.fetchone()[0] == 0:
                try:
                    mysql_cursor.execute(insert_query, row)
                    registros_inseridos += 1
                except mysql.connector.Error as err:
                    logger.error(f"Erro ao inserir registro no MySQL: {err} - Dados: {row}")
            else:
                registros_existentes += 1

        mysql_conn.commit()
        logger.info(f"{registros_inseridos} registros inseridos na tabela nfe do MySQL.")
        logger.info(f"{registros_existentes} registros já existiam na tabela nfe do MySQL e foram ignorados.")

    except cx_Oracle.Error as error:
        logger.error(f"Erro ao conectar ou executar query no Oracle: {error}")
    except Exception as e:
        logger.error(f"Erro inesperado durante a importação: {e}")
    finally:
        # Fechar as conexões usando a função do database.py
        if oracle_cursor:
            oracle_cursor.close()
        if oracle_conn:
            close_connection(oracle_conn)
            logger.info("Conexão com o banco de dados Oracle fechada.")
        if mysql_cursor:
            mysql_cursor.close()
        if mysql_conn:
            close_connection(mysql_conn)
            logger.info("Conexão com o banco de dados MySQL fechada.")

def init_sync(data_limite_oracle: Optional[str] = None,
                       log_level: Optional[int] = None,
                       log_format: Optional[str] = None):
    """
    Inicializa o módulo de sincronização de NF-es do Oracle para o MySQL com configurações personalizadas.

    Esta função configura o logging para o módulo e permite definir parâmetros como a data limite
    para a busca de dados no Oracle e o formato das mensagens de log. Após a configuração,
    ela inicia o processo de importação chamando a função `importar_nfes_oracle_mysql`.

    Args:
        data_limite_oracle: Data limite para buscar dados no Oracle (opcional,
                            formato 'YYYY-MM-DD HH24:MI:SS.FF3'). Se fornecido,
                            sobrescreve o valor padrão configurado.
        log_level: Nível de logging a ser utilizado (opcional). Os níveis comuns são:
                   - `logging.DEBUG`
                   - `logging.INFO` (padrão)
                   - `logging.WARNING`
                   - `logging.ERROR`
                   - `logging.CRITICAL`
        log_format: Formato da mensagem de log (opcional). O formato padrão é
                    '%(asctime)s - %(levelname)s - %(message)s'. Consulte a
                    documentação do módulo `logging` do Python para mais opções.

    Returns:
        None
    """
    if log_level is not None:
        _config['log_level'] = log_level
    if log_format is not None:
        _config['log_format'] = log_format
    if data_limite_oracle is not None:
        _config['data_limite_oracle'] = data_limite_oracle

    logging.basicConfig(level=_config['log_level'], format=_config['log_format'])
    logger.info(f"Módulo de sincronização de NF-es inicializado com configuração: {_config}")
    importar_nfes_oracle_mysql()
    logger.info("Processo de sincronização de NF-es concluído.")

if __name__ == "__main__":
    init_sync()