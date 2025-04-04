import logging
from typing import Optional
import mysql.connector
from modules.database import get_mysql_connection

logger = logging.getLogger(__name__)

# Variável para controle de inicialização
_initialized = False

# Dicionário para armazenar o mapeamento de código de ocorrência para descrição da categoria
CODIGO_PARA_CATEGORIA = {}

def init_status(conn: mysql.connector.MySQLConnection):
    """
    Inicializa o módulo de status carregando as descrições de status do banco de dados.

    Args:
        conn: Uma conexão ativa com o banco de dados MySQL.
    """
    global _initialized, CODIGO_PARA_CATEGORIA

    if _initialized:
        return

    CODIGO_PARA_CATEGORIA = {}
    cursor = conn.cursor()
    try:
        # Busca todas as ocorrências com suas categorias
        cursor.execute("""
            SELECT o.CODIGO_SSW, nc.DESCRICAO
            FROM ocorrencias o
            JOIN nfe_categorias nc ON o.categoria_id = nc.id
        """)
        ocorrencias_categorias = cursor.fetchall()
        for codigo, descricao in ocorrencias_categorias:
            CODIGO_PARA_CATEGORIA[codigo] = descricao.upper()
        logger.info(f"Mapeamento de códigos de ocorrência carregado do banco de dados: {len(CODIGO_PARA_CATEGORIA)} registros.")
        _initialized = True
    except mysql.connector.Error as err:
        logger.error(f"Erro ao carregar mapeamento de status do banco de dados: {err}")
    finally:
        cursor.close()

def determinar_status(conn: mysql.connector.MySQLConnection, ultimo_evento: Optional[str]) -> str:
    """
    Determina o status da NF-e com base no último evento e nas categorias do banco de dados.

    Args:
        conn: Uma conexão ativa com o banco de dados MySQL.
        ultimo_evento: O código do último evento da tabela nfe_status.

    Returns:
        str: Status da NF-e: "ENTREGUE", "PROBLEMA", "EM_TRANSITO" ou "NAO_ENCONTRADO".
    """
    if not _initialized:
        logger.warning("Módulo de status não foi inicializado. Execute init_status antes de determinar o status.")
        return "EM_TRANSITO"  # Retorno padrão caso não inicializado

    if not ultimo_evento:
        return "NAO_ENCONTRADO"

    categoria = CODIGO_PARA_CATEGORIA.get(ultimo_evento)

    if categoria == "ENTREGUE":
        return "ENTREGUE"
    elif categoria == "PROBLEMA":
        return "PROBLEMA"
    # Se a categoria não for explicitamente ENTREGUE ou PROBLEMA, consideramos EM_TRANSITO
    # Você pode adicionar mais categorias conforme necessário (ex: EM_TRANSITO diretamente na nfe_categorias)
    else:
        return "EM_TRANSITO"

# Função para inicializar o módulo (deve ser chamada na inicialização da aplicação)
def inicializar_status_app():
    conn = get_mysql_connection()
    if conn:
        init_status(conn)
        conn.close()
    else:
        logger.error("Falha ao obter conexão com o banco de dados para inicializar o módulo de status.")

# Função auxiliar para obter a conexão (você já tem isso em modules/database.py)

def inicializar_status_teste():
    """
    Inicializa o módulo de status para testes, obtendo uma conexão de banco de dados.
    """
    conn = get_mysql_connection()
    if conn:
        init_status(conn)
        conn.close()
    else:
        logger.error("Falha ao obter conexão com o banco de dados para inicializar o módulo de status para testes.")

if __name__ == "__main__":
    inicializar_status_teste()
    print("Módulo de status inicializado para testes.")

    conn = get_mysql_connection()
    if conn:
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT NUM_NF, ultimo_evento FROM nfe_status WHERE NUM_NF IS NOT NULL AND NUM_NF != ''")
            nfes_status = cursor.fetchall()

            status_counts = {'ENTREGUE': 0, 'PROBLEMA': 0, 'EM_TRANSITO': 0, 'NAO_ENCONTRADO': 0}

            for nfe in nfes_status:
                ultimo_evento = nfe.get('ultimo_evento')
                status_nf = determinar_status(conn, ultimo_evento)
                status_counts[status_nf] += 1

            print("\nContagem de NFs por status:")
            for status, count in status_counts.items():
                print(f"{status}: {count}")

        except mysql.connector.Error as err:
            logger.error(f"Erro ao buscar status das NFs: {err}")
        finally:
            cursor.close()
            conn.close()
    else:
        logger.error("Falha ao obter conexão com o banco de dados para o teste de status das NFs.")