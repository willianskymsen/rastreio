# modules/nfe_tracking_logger.py
import logging
import mysql.connector
import re  # Importa o módulo de expressões regulares
from modules.database import get_mysql_connection, close_connection

logger = logging.getLogger(__name__)

def init_logger():
    """Inicializa o logger para este módulo."""
    # A inicialização básica do logger já está feita fora da função.
    # Podemos adicionar configurações mais específicas aqui no futuro, se necessário.
    pass

def insert_evento(cursor_main, chave_nfe, num_nf, evento, status, transportadora, cidade, uf):
    """Função auxiliar para inserir um evento no banco"""
    try:
        # Prepara os dados para inserção
        descricao_completa = evento.get("descricao", "")
        codigo_ocorrencia = evento.get("codigo_ocorrencia", "")
        tipo_ocorrencia = evento.get("ocorrencia", "").strip()

        # Fallback para código de ocorrência se não encontrado no texto pelo json_parser
        if not codigo_ocorrencia:
            conn_fallback = None
            cursor_fallback = None
            try:
                 conn_fallback = get_mysql_connection()
                 if conn_fallback:
                      cursor_fallback = conn_fallback.cursor()
                      cursor_fallback.execute(
                           "SELECT CODIGO_SSW FROM ocorrencias WHERE DESCRICAO = %s",
                           (tipo_ocorrencia,)
                      )
                      resultado = cursor_fallback.fetchone()
                      if resultado:
                           codigo_ocorrencia = resultado[0]
                      else:
                           codigo_ocorrencia = "99"
                 else:
                      logger.error("Falha ao obter conexão com o banco de dados para fallback de código de ocorrência.")
                      codigo_ocorrencia = "99" # Define como 99 em caso de falha na conexão
            finally:
                 if cursor_fallback:
                      cursor_fallback.close()
                 if conn_fallback:
                      close_connection(conn_fallback)

            cursor_main.execute(
               """
               INSERT INTO nfe_logs
               (chave_nfe, NUM_NF, codigo_ocorrencia, tipo_ocorrencia, cidade_ocorrencia,
                 dominio, filial, nome_recebedor, documento_recebedor, descricao_completa,
                 data_hora, status, transportadora, cidade, uf)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE
                  descricao_completa = VALUES(descricao_completa),
                  status = VALUES(status),
                  tipo_ocorrencia = VALUES(tipo_ocorrencia),
                  cidade_ocorrencia = VALUES(cidade_ocorrencia)
                """,
                (
                  chave_nfe, num_nf,
                  codigo_ocorrencia,
                  tipo_ocorrencia,
                  evento.get("cidade", ""),
                  evento.get("dominio", ""),
                  evento.get("filial", ""),
                  evento.get("nome_recebedor", ""),
                  evento.get("nro_doc_recebedor", ""),
                  descricao_completa,
                  evento.get("data_hora"),
                  status,
                  transportadora,
                  cidade,
                  uf
            )
        )
    except mysql.connector.Error as e:
          logger.warning(f"Evento já existe para NF-e {num_nf}, atualizando dados: {str(e)}")

def insert_default_status(cursor, chave_nfe, num_nf, transportadora, cidade, uf, dt_saida, ultimo_evento):
    """Função auxiliar para inserir status padrão quando não encontra dados"""
    # Verifica se a chave_nfe já existe
    cursor.execute("SELECT COUNT(*) FROM nfe_status WHERE chave_nfe = %s", (chave_nfe,))
    existe = cursor.fetchone()[0]

    if existe == 0:
        # Só insere se não existir
        cursor.execute(
            """
            INSERT INTO nfe_status
            (chave_nfe, NUM_NF, ultimo_evento, data_hora, status, transportadora, cidade, uf, dt_saida)
            VALUES (%s, %s, %s, NOW(), %s, %s, %s, %s, %s)
            """,
            (
                chave_nfe, num_nf,
                ultimo_evento,  # Usando o valor passado
                "NAO_ENCONTRADO",
                transportadora,
                cidade,
                uf,
                dt_saida
            )
        )
    else:
        logger.info(f"NF-e {chave_nfe} já existe na tabela `nfe_status`, ignorando inserção.")
