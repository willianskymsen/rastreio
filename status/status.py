from flask import Blueprint, render_template, request, jsonify
from modules.database import get_mysql_connection
from modules.logger_config import logger
import mysql.connector

status_blueprint = Blueprint('status', __name__, template_folder='templates', static_folder='static')

@status_blueprint.route("/")
def status():
    return render_template("ocorrencias.html")

@status_blueprint.route("/vincular-ocorrencias")
def categorias():
    return render_template("categorias.html")

@status_blueprint.route("/api/ocorrencias", methods=["GET"])
def api_ocorrencias():
    conn = None
    try:
        conn = get_mysql_connection()
        if not conn:
            return jsonify({"error": "Falha na conexão com o MySQL"}), 500

        cursor = conn.cursor(dictionary=True)
        query = "SELECT CODIGO_SSW, DESCRICAO, COD_INTERNO FROM ocorrencias WHERE ATIVO = 1 AND categoria_id IS NULL" # Removendo TIPO e PROCESSO, adicionando COD_INTERNO
        tipo_filtro = request.args.get('tipo')
        if tipo_filtro:
            # Não podemos mais filtrar por TIPO, então removemos essa lógica
            pass
        else:
            cursor.execute(query)

        ocorrencias = cursor.fetchall()
        conn.close()

        logger.info(f"Dados ativos e não vinculados da tabela ocorrencias buscados com sucesso. Total de registros: {len(ocorrencias)}")
        print("DEBUG: Retornando JSON")
        return jsonify(ocorrencias)

    except mysql.connector.Error as db_error:
        logger.error(f"Erro de banco de dados ao buscar dados da tabela ocorrencias: {db_error}")
        print(f"DEBUG: Erro de banco de dados: {db_error}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Erro ao buscar dados no banco de dados", "details": str(db_error)}), 500
    except Exception as e:
        logger.error(f"Erro inesperado ao buscar dados da tabela ocorrencias: {e}")
        print(f"DEBUG: Erro inesperado: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Erro interno ao buscar dados", "details": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            print("DEBUG: Fechando conexão no finally")
            conn.close()
        else:
            print("DEBUG: Conexão já fechada ou inexistente no finally")

@status_blueprint.route("/api/ocorrencias", methods=["POST"])
def adicionar_ocorrencia():
    conn = None
    try:
        data = request.json
        codigo_ssw = data.get("CODIGO_SSW")
        descricao = data.get("DESCRICAO")

        if not all([codigo_ssw, descricao]): # Removendo a obrigatoriedade de TIPO e PROCESSO
            return jsonify({"error": "Os campos CODIGO_SSW e DESCRICAO são obrigatórios"}), 400

        conn = get_mysql_connection()
        if not conn:
            return jsonify({"error": "Falha na conexão com o MySQL"}), 500

        cursor = conn.cursor()
        query = "INSERT INTO ocorrencias (CODIGO_SSW, DESCRICAO, ATIVO) VALUES (%s, %s, %s)" # Removendo TIPO e PROCESSO
        cursor.execute(query, (codigo_ssw, descricao, 1))
        conn.commit()
        conn.close()

        logger.info(f"Ocorrência com CODIGO_SSW {codigo_ssw} adicionada com sucesso.")
        return jsonify({"message": "Ocorrência adicionada com sucesso."}), 201

    except mysql.connector.Error as db_error:
        logger.error(f"Erro de banco de dados ao adicionar ocorrência: {db_error}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Erro ao adicionar ocorrência no banco de dados", "details": str(db_error)}), 500
    except Exception as e:
        logger.error(f"Erro inesperado ao adicionar ocorrência: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Erro interno ao adicionar ocorrência", "details": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()

@status_blueprint.route("/api/ocorrencias/<int:codigo_ssw>", methods=["PUT"])
def inativar_ocorrencia(codigo_ssw):
    conn = None
    try:
        conn = get_mysql_connection()
        if not conn:
            return jsonify({"error": "Falha na conexão com o MySQL"}), 500

        cursor = conn.cursor()
        query = "UPDATE ocorrencias SET ATIVO = 0 WHERE CODIGO_SSW = %s"
        cursor.execute(query, (codigo_ssw,))
        conn.commit()
        conn.close()

        logger.info(f"Ocorrência com CODIGO_SSW {codigo_ssw} inativada com sucesso.")
        return jsonify({"message": "Ocorrência inativada com sucesso."}), 200

    except mysql.connector.Error as db_error:
        logger.error(f"Erro de banco de dados ao inativar ocorrência: {db_error}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Erro ao inativar ocorrência no banco de dados", "details": str(db_error)}), 500
    except Exception as e:
        logger.error(f"Erro inesperado ao inativar ocorrência: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Erro interno ao inativar ocorrência", "details": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()

@status_blueprint.route("/api/ocorrencias/<int:codigo_ssw>/editar", methods=["PUT"])
def editar_ocorrencia(codigo_ssw):
    conn = None
    try:
        data = request.json
        descricao = data.get("DESCRICAO")

        if not descricao: # Removendo a obrigatoriedade de TIPO e PROCESSO
            return jsonify({"error": "O campo DESCRICAO para edição é obrigatório"}), 400

        conn = get_mysql_connection()
        if not conn:
            return jsonify({"error": "Falha na conexão com o MySQL"}), 500

        cursor = conn.cursor()
        query = "UPDATE ocorrencias SET DESCRICAO = %s WHERE CODIGO_SSW = %s" # Removendo TIPO e PROCESSO
        cursor.execute(query, (descricao, codigo_ssw))
        conn.commit()
        conn.close()

        logger.info(f"Ocorrência com CODIGO_SSW {codigo_ssw} editada com sucesso.")
        return jsonify({"message": "Ocorrência editada com sucesso."}), 200

    except mysql.connector.Error as db_error:
        logger.error(f"Erro de banco de dados ao editar ocorrência: {db_error}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Erro ao editar ocorrência no banco de dados", "details": str(db_error)}), 500
    except Exception as e:
        logger.error(f"Erro inesperado ao editar ocorrência: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Erro interno ao editar ocorrência", "details": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()

@status_blueprint.route("/api/ocorrencias/pendentes", methods=["GET"])
def api_ocorrencias_pendentes():
    conn = None
    try:
        conn = get_mysql_connection()
        if not conn:
            return jsonify({"error": "Falha na conexão com o MySQL"}), 500

        cursor = conn.cursor(dictionary=True)
        query = "SELECT DISTINCT tipo_ocorrencia, MIN(id) as id FROM nfe_logs WHERE codigo_ocorrencia = '999' GROUP BY tipo_ocorrencia"
        cursor.execute(query)
        ocorrencias_pendentes = cursor.fetchall()
        conn.close()

        logger.info(f"Dados distintos de tipo_ocorrencia com codigo_ocorrencia '999' buscados com sucesso. Total de registros: {len(ocorrencias_pendentes)}")
        return jsonify(ocorrencias_pendentes)

    except mysql.connector.Error as db_error:
        logger.error(f"Erro de banco de dados ao buscar dados de ocorrências pendentes: {db_error}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Erro ao buscar dados no banco de dados", "details": str(db_error)}), 500
    except Exception as e:
        logger.error(f"Erro inesperado ao buscar dados de ocorrências pendentes: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Erro interno ao buscar dados", "details": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()

@status_blueprint.route("/api/ocorrencias/pendentes/<int:id>/atribuir-codigo", methods=["PUT"])
def atribuir_codigo_ocorrencia_pendente(id):
    conn = None
    try:
        data = request.json
        novo_codigo = data.get("novo_codigo")
        tipo = data.get("tipo") # Mantendo para usar como descrição fallback
        # processo = data.get("processo") # Removido da inserção em ocorrencias

        if not novo_codigo:
            return jsonify({"error": "O campo 'novo_codigo' é obrigatório"}), 400

        conn = get_mysql_connection()
        if not conn:
            return jsonify({"error": "Falha na conexão com o MySQL"}), 500

        cursor = conn.cursor()

        # Atualiza o codigo_ocorrencia na tabela nfe_logs
        cursor.execute(
            "UPDATE nfe_logs SET codigo_ocorrencia = %s WHERE id = %s AND codigo_ocorrencia = '999'",
            (novo_codigo, id),
        )

        # Busca o tipo_ocorrencia para usar como descrição (se necessário)
        cursor.execute("SELECT tipo_ocorrencia FROM nfe_logs WHERE id = %s", (id,))
        nfe_log = cursor.fetchone()
        descricao_ocorrencia = nfe_log[0] if nfe_log else tipo  # Usa o tipo se nfe_log não encontrado

        # Insere na tabela ocorrencias
        insert_ocorrencias_query = (
            "INSERT INTO ocorrencias (CODIGO_SSW, DESCRICAO) VALUES (%s, %s)" # Removendo TIPO e PROCESSO
        )
        cursor.execute(insert_ocorrencias_query, (novo_codigo, descricao_ocorrencia))
        conn.commit()

        logger.info(
            f"Código '{novo_codigo}' atribuído à ocorrência pendente (ID: {id}) na tabela nfe_logs e inserido na tabela ocorrencias."
        )
        return jsonify(
            {
                "message": f"Código '{novo_codigo}' atribuído com sucesso à ocorrência."
            }
        ), 200

    except mysql.connector.Error as db_error:
        logger.error(f"Erro de banco de dados ao atribuir código: {db_error}")
        if conn:
            conn.rollback()
        return (
            jsonify(
                {"error": "Erro ao atribuir código no banco de dados", "details": str(db_error)}
            ),
            500,
        )
    except Exception as e:
        logger.error(f"Erro inesperado ao atribuir código: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Erro interno ao atribuir código", "details": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()

@status_blueprint.route("/api/ocorrencias/pendentes/<int:id>/remover", methods=["DELETE"])
def remover_ocorrencia_pendente(id):
    conn = None
    try:
        conn = get_mysql_connection()
        if not conn:
            return jsonify({"error": "Falha na conexão com o MySQL"}), 500

        cursor = conn.cursor()
        cursor.execute("DELETE FROM nfe_logs WHERE id = %s AND codigo_ocorrencia = '999'", (id,))
        conn.commit()

        if cursor.rowcount > 0:
            logger.info(f"Ocorrência pendente com ID {id} removida com sucesso.")
            return jsonify({"message": f"Ocorrência pendente com ID {id} removida com sucesso."}), 200
        else:
            return jsonify({"error": f"Ocorrência pendente com ID {id} não encontrada ou já foi processada."}), 404

    except mysql.connector.Error as db_error:
        logger.error(f"Erro de banco de dados ao remover ocorrência pendente: {db_error}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Erro ao remover ocorrência pendente no banco de dados", "details": str(db_error)}), 500
    except Exception as e:
        logger.error(f"Erro inesperado ao remover ocorrência pendente: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Erro interno ao remover ocorrência pendente", "details": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()

@status_blueprint.route("/api/ocorrencias/pendentes/<int:id>", methods=["GET"])
def get_ocorrencia_pendente(id):
    conn = None
    try:
        conn = get_mysql_connection()
        if not conn:
            return jsonify({"error": "Falha na conexão com o MySQL"}), 500

        cursor = conn.cursor()
        # Select tipo_ocorrencia
        cursor.execute(
            "SELECT tipo_ocorrencia FROM nfe_logs WHERE id = %s AND codigo_ocorrencia = '999'",
            (id,),
        )
        resultado = cursor.fetchone()

        if resultado:
            ocorrencia = {
                "tipo_ocorrencia": resultado[0],
                "processo": None, # Processo não está em nfe_logs
            }
            return jsonify(ocorrencia), 200
        else:
            return jsonify({"error": f"Ocorrência pendente com ID {id} não encontrada."}), 404

        # ... (tratamento de erros e fechamento de conexão)

    except mysql.connector.Error as db_error:
        logger.error(f"Erro de banco de dados ao buscar ocorrência pendente: {db_error}")
        return (
            jsonify(
                {"error": "Erro ao buscar ocorrência no banco de dados", "details": str(db_error)}
            ),
            500,
        )
    except Exception as e:
        logger.error(f"Erro inesperado ao buscar ocorrência pendente: {e}")
        return jsonify({"error": "Erro interno ao buscar ocorrência", "details": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()

@status_blueprint.route("/api/ocorrencias/vincular-categoria", methods=["PUT"])
def vincular_codigo_categoria():
    conn = None
    try:
        data = request.json
        codigo_ssw = data.get("codigo_ssw")
        transportadora_id = data.get("transportadora_id")
        descricao_categoria = data.get("descricao_categoria")  # Novo campo para a descrição

        if not all([codigo_ssw, transportadora_id, descricao_categoria]):
            return jsonify({"error": "Os campos 'codigo_ssw', 'transportadora_id' e 'descricao_categoria' são obrigatórios."}), 400

        conn = get_mysql_connection()
        if not conn:
            return jsonify({"error": "Falha na conexão com o MySQL"}), 500

        cursor = conn.cursor()
        query = "UPDATE nfe_categorias SET DESCRICAO = %s WHERE transportadora_id = %s AND DATE(created_at) = CURDATE()" # Usando created_at como referência de data
        cursor.execute(query, (descricao_categoria, transportadora_id))

        if cursor.rowcount == 0:
            # Se não houver linha para hoje, tenta inserir uma nova
            insert_query = "INSERT INTO nfe_categorias (DESCRICAO, transportadora_id) VALUES (%s, %s)" # created_at e updated_at serão automáticos
            cursor.execute(insert_query, (descricao_categoria, transportadora_id))

        conn.commit()
        conn.close()

        logger.info(f"Código '{codigo_ssw}' vinculado à descrição '{descricao_categoria}' para transportadora {transportadora_id}.")
        return jsonify({"message": f"Código '{codigo_ssw}' vinculado à descrição '{descricao_categoria}' com sucesso."}), 200

    except mysql.connector.Error as db_error:
        logger.error(f"Erro de banco de dados ao vincular código à categoria: {db_error}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Erro ao vincular código à categoria no banco de dados", "details": str(db_error)}), 500
    except Exception as e:
        logger.error(f"Erro inesperado ao vincular código à categoria: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Erro interno ao vincular código à categoria", "details": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()

@status_blueprint.route("/api/categorias", methods=["POST"])
def criar_categoria():
    conn = None
    try:
        data = request.json
        descricao = data.get("descricao") # Campo para a descrição

        if not descricao:
            return jsonify({"error": "O campo 'descricao' é obrigatório."}), 400

        conn = get_mysql_connection()
        if not conn:
            return jsonify({"error": "Falha na conexão com o MySQL"}), 500

        cursor = conn.cursor()
        query = "INSERT INTO nfe_categorias (DESCRICAO) VALUES (%s)" # created_at e updated_at serão automáticos
        cursor.execute(query, (descricao,))
        conn.commit()
        conn.close()

        logger.info(f"Nova categoria criada com descrição '{descricao}'.")
        return jsonify({"message": "Categoria criada com sucesso."}), 201

    except mysql.connector.Error as db_error:
        logger.error(f"Erro de banco de dados ao criar categoria: {db_error}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Erro ao criar categoria no banco de dados", "details": str(db_error)}), 500
    except Exception as e:
        logger.error(f"Erro inesperado ao criar categoria: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Erro interno ao criar categoria", "details": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()

@status_blueprint.route("/api/categorias", methods=["GET"])
def get_categorias():
    conn = None
    try:
        conn = get_mysql_connection()
        if not conn:
            return jsonify({"error": "Falha na conexão com o MySQL"}), 500

        cursor = conn.cursor(dictionary=True)
        query = "SELECT id, DESCRICAO FROM nfe_categorias"
        cursor.execute(query)
        categorias = cursor.fetchall()
        conn.close()

        logger.info(f"Dados da tabela nfe_categorias buscados com sucesso. Total de registros: {len(categorias)}")
        return jsonify(categorias)

    except mysql.connector.Error as db_error:
        logger.error(f"Erro de banco de dados ao buscar categorias: {db_error}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Erro ao buscar categorias no banco de dados", "details": str(db_error)}), 500
    except Exception as e:
        logger.error(f"Erro inesperado ao buscar categorias: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Erro interno ao buscar categorias", "details": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()

@status_blueprint.route("/api/ocorrencias/vincular", methods=["PUT"])
def vincular_ocorrencias():
    conn = None
    try:
        data = request.json
        categoria_id = data.get("categoria_id")
        ocorrencias = data.get("ocorrencias")

        if not categoria_id or not isinstance(ocorrencias, list) or not ocorrencias:
            return jsonify({"error": "Os campos 'categoria_id' e 'ocorrencias' são obrigatórios e 'ocorrencias' deve ser uma lista não vazia."}), 400

        conn = get_mysql_connection()
        if not conn:
            return jsonify({"error": "Falha na conexão com o MySQL"}), 500

        cursor = conn.cursor()
        query = "UPDATE ocorrencias SET categoria_id = %s WHERE CODIGO_SSW = %s"

        for codigo_ssw in ocorrencias:
            cursor.execute(query, (categoria_id, codigo_ssw))

        conn.commit()
        conn.close()

        logger.info(f"Vinculadas {cursor.rowcount} ocorrências à categoria ID {categoria_id}.")
        return jsonify({"message": f"{cursor.rowcount} ocorrências vinculadas com sucesso à categoria ID {categoria_id}."}), 200

    except mysql.connector.Error as db_error:
        logger.error(f"Erro de banco de dados ao vincular ocorrências: {db_error}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Erro ao vincular ocorrências no banco de dados", "details": str(db_error)}), 500
    except Exception as e:
        logger.error(f"Erro inesperado ao vincular ocorrências: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Erro interno ao vincular ocorrências", "details": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()

@status_blueprint.route("/api/categorias/<int:categoria_id>/ocorrencias", methods=["GET"])
def get_ocorrencias_por_categoria(categoria_id):
    conn = None
    try:
        conn = get_mysql_connection()
        if not conn:
            return jsonify({"error": "Falha na conexão com o MySQL"}), 500

        cursor = conn.cursor(dictionary=True)
        query = "SELECT CODIGO_SSW, DESCRICAO FROM ocorrencias WHERE categoria_id = %s"
        cursor.execute(query, (categoria_id,))
        ocorrencias_vinculadas = cursor.fetchall()
        conn.close()

        logger.info(f"Ocorrências vinculadas à categoria ID {categoria_id} buscadas com sucesso. Total de registros: {len(ocorrencias_vinculadas)}")
        return jsonify(ocorrencias_vinculadas)

    except mysql.connector.Error as db_error:
        logger.error(f"Erro de banco de dados ao buscar ocorrências por categoria: {db_error}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Erro ao buscar ocorrências no banco de dados", "details": str(db_error)}), 500
    except Exception as e:
        logger.error(f"Erro inesperado ao buscar ocorrências por categoria: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Erro interno ao buscar ocorrências", "details": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()