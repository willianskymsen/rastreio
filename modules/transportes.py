import logging
from modules.database import get_oracle_connection, get_mysql_connection, close_connection

logger = logging.getLogger(__name__)

def transfer_transportadoras():
    # 1. Definir o filtro como variável (altere apenas aqui para mudar o critério)
    FILTRO_DESCRICAO = '%SETE LAGOAS TRANSPORTES LTDA%'
    NOME_FILTRO = FILTRO_DESCRICAO  # Nome amigável para logs
    
    oracle_conn = None
    mysql_conn = None
    cursor_oracle = None
    cursor_mysql = None
    
    try:
        # 2. Conectar ao Oracle e buscar os dados
        oracle_conn = get_oracle_connection()
        cursor_oracle = oracle_conn.cursor()
        
        query_oracle = f"""
            SELECT ID, COD_FOR, DESCRICAO, NOME_FAN, CNPJ, INSC_EST, INSC_MUN 
            FROM TFORNECEDORES 
            WHERE UPPER(DESCRICAO) LIKE '{FILTRO_DESCRICAO}'
        """
        
        cursor_oracle.execute(query_oracle)
        fornecedores = cursor_oracle.fetchall()
        
        if not fornecedores:
            logger.info(f"Nenhum fornecedor com '{NOME_FILTRO}' na descrição encontrado.")
            return
        
        logger.info(f"Encontrados {len(fornecedores)} fornecedores com '{NOME_FILTRO}' na descrição.")
        
        # 3. Conectar ao MySQL e inserir os dados
        mysql_conn = get_mysql_connection()
        cursor_mysql = mysql_conn.cursor()
        
        # Configurar para ignorar warnings
        cursor_mysql.execute("SET sql_notes = 0")
        
        # Verificar se a tabela transportadoras existe (corrigido NOME_FAN que estava como NOME_MAN)
        cursor_mysql.execute("""
            CREATE TABLE IF NOT EXISTS transportadoras (
                ID INT,
                COD_FOR VARCHAR(50),
                DESCRICAO VARCHAR(255),
                NOME_FAN VARCHAR(255),
                CNPJ VARCHAR(20),
                INSC_EST VARCHAR(50),
                INSC_MUN VARCHAR(50),
                SISTEMA VARCHAR(50) NULL,
                PRIMARY KEY (ID)
            )
        """)
        
        # Restaurar configuração padrão
        cursor_mysql.execute("SET sql_notes = 1")
        
        # Inserir os dados
        insert_query = """
            INSERT INTO transportadoras 
            (ID, COD_FOR, DESCRICAO, NOME_FAN, CNPJ, INSC_EST, INSC_MUN, SISTEMA) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                COD_FOR = VALUES(COD_FOR),
                DESCRICAO = VALUES(DESCRICAO),
                NOME_FAN = VALUES(NOME_FAN),
                CNPJ = VALUES(CNPJ),
                INSC_EST = VALUES(INSC_EST),
                INSC_MUN = VALUES(INSC_MUN),
                SISTEMA = VALUES(SISTEMA)
        """
        
        # Preparar os dados incluindo NULL para SISTEMA
        dados_com_sistema = [(*fornecedor, None) for fornecedor in fornecedores]
        
        cursor_mysql.executemany(insert_query, dados_com_sistema)
        mysql_conn.commit()
        
        logger.info(f"Dados inseridos/atualizados com sucesso: {cursor_mysql.rowcount} registros")
        
    except Exception as e:
        logger.error(f"Erro durante a transferência de dados para '{NOME_FILTRO}': {str(e)}")
        if mysql_conn:
            mysql_conn.rollback()
        raise
    finally:
        # Fechar cursos e conexões
        if cursor_oracle:
            cursor_oracle.close()
        if cursor_mysql:
            cursor_mysql.close()
        if oracle_conn:
            close_connection(oracle_conn)
        if mysql_conn:
            close_connection(mysql_conn)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    transfer_transportadoras()