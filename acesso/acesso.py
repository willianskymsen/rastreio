import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Blueprint, render_template, request, Flask, jsonify, redirect, url_for
from modules.database import get_mysql_connection
from modules.logger_config import logger
import mysql.connector
from datetime import datetime

acesso_blueprint = Blueprint('acesso', __name__, template_folder='templates', static_folder='static')

# Função auxiliar para determinar o status dinamicamente a partir do histórico
def determinar_status_dinamico(historico):
    if not historico:
        return "Status Indisponível", "indisponivel"
    ultimo_evento = historico[0]
    categoria_ocorrencia = ultimo_evento.get("categoria_ocorrencia", "").strip()
    if categoria_ocorrencia:
        return categoria_ocorrencia.title(), categoria_ocorrencia.lower().replace(" ", "-")
    return "Status Desconhecido", "desconhecido"

@acesso_blueprint.route("/home")
def index():
    logger.debug("Rota / acessada - renderizando página inicial.")
    return render_template("rastreio.html")

@acesso_blueprint.route("/acesso")
def rastreio_token():
    logger.info("Rota /acesso acessada.")
    token = request.args.get('chave')
    logger.debug(f"Parâmetro recebido - chave: {token}")

    if not token:
        logger.warning("Requisição para /acesso sem o parâmetro 'chave'.")
        return render_template("erro.html", mensagem="URL inválida: parâmetro 'chave' não encontrado.")

    conn = None
    try:
        logger.info("Tentando conectar ao banco de dados...")
        conn = get_mysql_connection()
        logger.info("Conexão com o banco de dados estabelecida com sucesso.")
        cursor = conn.cursor(dictionary=True)

        # Consulta para obter o NUM_NF
        query_token = "SELECT NUM_NF FROM transporte.nfe_tokens WHERE token = %s"
        params_token = (token,)
        logger.debug(f"Executando query_token: {query_token} | Parâmetros: {params_token}")
        try:
            cursor.execute(query_token, params_token)
            result_token = cursor.fetchone()
            logger.debug(f"Resultado da query_token: {result_token}")
        except mysql.connector.Error as err:
            logger.error(f"Erro ao executar query (token): {err}")
            raise

        if result_token:
            num_nf = result_token['NUM_NF']
            logger.info(f"Token válido. NUM_NF encontrado: {num_nf}")
            response_data = {'NUM_NF': num_nf}

            # Histórico de rastreamento
            with conn.cursor(dictionary=True) as cursor_logs:
                query_logs = """
                    SELECT
                        nl.codigo_ocorrencia,
                        o.DESCRICAO AS descricao_ocorrencia,
                        nc.DESCRICAO AS categoria_ocorrencia,
                        nl.descricao_completa,
                        nl.data_hora,
                        nl.status,
                        nl.cidade_ocorrencia,
                        nl.uf,
                        nl.dominio,
                        nl.filial,
                        nl.nome_recebedor,
                        nl.documento_recebedor
                    FROM transporte.nfe_logs nl
                    JOIN transporte.ocorrencias o ON nl.codigo_ocorrencia = o.CODIGO_SSW
                    LEFT JOIN transporte.nfe_categorias nc ON o.categoria_id = nc.id
                    WHERE nl.NUM_NF = %s
                    ORDER BY nl.data_hora DESC
                """
                params_logs = (num_nf,)
                logger.debug(f"Executando query_logs: {query_logs} | Parâmetros: {params_logs}")
                try:
                    cursor_logs.execute(query_logs, params_logs)
                    historico = cursor_logs.fetchall()
                    logger.debug(f"Resultado da query_logs: {historico}")
                    for item in historico:
                        if 'data_hora' in item and isinstance(item['data_hora'], datetime):
                            item['data_hora'] = item['data_hora'].strftime('%Y-%m-%dT%H:%M:%S')
                    response_data['historico_rastreamento'] = historico

                except mysql.connector.Error as err:
                    logger.error(f"Erro ao executar query (nfe_logs): {err}")
                    raise

            # Determinar status da remessa de forma dinâmica
            status_description, status_class = determinar_status_dinamico(historico)
            response_data['status_description'] = status_description
            response_data['status_class'] = status_class

            # Informações adicionais da NF
            with conn.cursor(dictionary=True) as cursor_nfe:
                query_nfe = """
                    SELECT NOME, PESO_BRT, QTD_VOLUMES
                    FROM transporte.nfe
                    WHERE NUM_NF = %s
                    LIMIT 1
                """
                params_nfe = (num_nf,)
                logger.debug(f"Executando query_nfe: {query_nfe} | Parâmetros: {params_nfe}")
                try:
                    cursor_nfe.execute(query_nfe, params_nfe)
                    nfe_info = cursor_nfe.fetchone()
                    logger.debug(f"Resultado da query_nfe: {nfe_info}")
                    if nfe_info:
                        response_data['destinatario'] = nfe_info.get('NOME')
                        response_data['peso'] = nfe_info.get('PESO_BRT')
                        response_data['volumes'] = nfe_info.get('QTD_VOLUMES')
                except mysql.connector.Error as err:
                    logger.error(f"Erro ao executar query (nfe): {err}")
                    raise
            
            # Obter a data e hora da última atualização da tabela nfe_status
            with conn.cursor(dictionary=True) as cursor_status:
                query_status = """
                    SELECT updated_at
                    FROM transporte.nfe_status
                    WHERE NUM_NF = %s
                    ORDER BY updated_at DESC
                    LIMIT 1
                """
                params_status = (num_nf,)
                logger.debug(f"Executando query_status: {query_status} | Parâmetros: {params_status}")
                try:
                    cursor_status.execute(query_status, params_status)
                    status_info = cursor_status.fetchone()
                    logger.debug(f"Resultado da query_status: {status_info}")
                    if status_info and status_info.get('updated_at'):
                        response_data['ultima_atualizacao'] = status_info['updated_at'].isoformat()
                    else:
                        response_data['ultima_atualizacao'] = None  # Ou algum valor padrão, se preferir
                except mysql.connector.Error as err:
                    logger.error(f"Erro ao executar query (nfe_status): {err}")
                    raise

            logger.info(f"Renderizando página de acesso para NUM_NF: {num_nf}")
            return render_template("rastreio.html", rastreamento_data=response_data, datetime=datetime)

        else:
            logger.warning(f"Token '{token}' não encontrado na base de dados.")
            return render_template("erro.html", mensagem="Token de acesso inválido.")

    except mysql.connector.Error as err:
        logger.critical(f"Erro ao conectar ou consultar o banco de dados (nível superior): {err}")
        return render_template("erro.html", mensagem="Erro interno ao verificar o token.")
    except Exception as e:
        logger.error(f"Ocorreu um erro inesperado: {e}")
        return render_template("erro.html", mensagem="Ocorreu um erro inesperado.")
    finally:
        if conn and conn.is_connected():
            conn.close()
            logger.info("Conexão com o banco de dados encerrada.")

# Nova rota API para enviar os dados de rastreamento para o front-end em formato JSON
@acesso_blueprint.route("/api/acesso")
def api_rastreio():
    logger.info("Rota /api/acesso acessada.")
    token = request.args.get('chave')
    logger.debug(f"Parâmetro recebido - chave: {token}")

    if not token:
        logger.warning("Requisição para /api/acesso sem o parâmetro 'chave'.")
        return jsonify({"erro": "URL inválida: parâmetro 'chave' não encontrado."}), 400

    conn = None
    try:
        logger.info("Tentando conectar ao banco de dados...")
        conn = get_mysql_connection()
        logger.info("Conexão com o banco de dados estabelecida com sucesso.")
        cursor = conn.cursor(dictionary=True)

        # Consulta para obter o NUM_NF
        query_token = "SELECT NUM_NF FROM transporte.nfe_tokens WHERE token = %s"
        params_token = (token,)
        logger.debug(f"Executando query_token: {query_token} | Parâmetros: {params_token}")
        try:
            cursor.execute(query_token, params_token)
            result_token = cursor.fetchone()
            logger.debug(f"Resultado da query_token: {result_token}")
        except mysql.connector.Error as err:
            logger.error(f"Erro ao executar query (token): {err}")
            return jsonify({"erro": "Erro ao consultar token."}), 500

        if result_token:
            num_nf = result_token['NUM_NF']
            logger.info(f"Token válido. NUM_NF encontrado: {num_nf}")
            response_data = {'NUM_NF': num_nf}

            # Histórico de rastreamento
            with conn.cursor(dictionary=True) as cursor_logs:
                query_logs = """
                    SELECT
                        nl.codigo_ocorrencia,
                        o.DESCRICAO AS descricao_ocorrencia,
                        nc.DESCRICAO AS categoria_ocorrencia,
                        nl.descricao_completa,
                        nl.data_hora,
                        nl.status,
                        nl.cidade_ocorrencia,
                        nl.uf,
                        nl.dominio,
                        nl.filial,
                        nl.nome_recebedor,
                        nl.documento_recebedor
                    FROM transporte.nfe_logs nl
                    JOIN transporte.ocorrencias o ON nl.codigo_ocorrencia = o.CODIGO_SSW
                    LEFT JOIN transporte.nfe_categorias nc ON o.categoria_id = nc.id
                    WHERE nl.NUM_NF = %s
                    ORDER BY nl.data_hora DESC
                """
                params_logs = (num_nf,)
                logger.debug(f"Executando query_logs: {query_logs} | Parâmetros: {params_logs}")
                try:
                    cursor_logs.execute(query_logs, params_logs)
                    historico = cursor_logs.fetchall()
                    logger.debug(f"Resultado da query_logs: {historico}")
                    for item in historico:
                        if 'data_hora' in item and isinstance(item['data_hora'], datetime):
                            item['data_hora'] = item['data_hora'].strftime('%Y-%m-%dT%H:%M:%S')
                    response_data['historico_rastreamento'] = historico

                    # Determinar status da remessa de forma dinâmica
                    status_description, status_class = determinar_status_dinamico(historico)
                    response_data['status_description'] = status_description
                    response_data['status_class'] = status_class

                except mysql.connector.Error as err:
                    logger.error(f"Erro ao executar query (nfe_logs): {err}")
                    return jsonify({"erro": "Erro ao consultar histórico de rastreamento."}), 500

            # Informações adicionais da NF
            with conn.cursor(dictionary=True) as cursor_nfe:
                query_nfe = """
                    SELECT NOME, PESO_BRT, QTD_VOLUMES
                    FROM transporte.nfe
                    WHERE NUM_NF = %s
                    LIMIT 1
                """
                params_nfe = (num_nf,)
                logger.debug(f"Executando query_nfe: {query_nfe} | Parâmetros: {params_nfe}")
                try:
                    cursor_nfe.execute(query_nfe, params_nfe)
                    nfe_info = cursor_nfe.fetchone()
                    logger.debug(f"Resultado da query_nfe: {nfe_info}")
                    if nfe_info:
                        response_data['destinatario'] = nfe_info.get('NOME')
                        response_data['peso'] = nfe_info.get('PESO_BRT')
                        response_data['volumes'] = nfe_info.get('QTD_VOLUMES')
                except mysql.connector.Error as err:
                    logger.error(f"Erro ao executar query (nfe): {err}")
                    return jsonify({"erro": "Erro ao consultar informações da NF."}), 500

            logger.info(f"Enviando dados de rastreamento para NUM_NF: {num_nf}")
            return jsonify(response_data)

        else:
            logger.warning(f"Token '{token}' não encontrado na base de dados.")
            return jsonify({"erro": "Token de rastreio inválido."}), 404

    except mysql.connector.Error as err:
        logger.critical(f"Erro ao conectar ou consultar o banco de dados (nível superior): {err}")
        return jsonify({"erro": "Erro interno ao verificar o token."}), 500
    except Exception as e:
        logger.error(f"Ocorreu um erro inesperado: {e}")
        return jsonify({"erro": "Ocorreu um erro inesperado."}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()
            logger.info("Conexão com o banco de dados encerrada.")

@acesso_blueprint.route("/erro")
def erro():
    mensagem = request.args.get('mensagem', 'Ocorreu um erro.')
    logger.debug(f"Rota /erro acessada com mensagem: {mensagem}")
    return render_template("erro.html", mensagem=mensagem)

# Nova rota para entrada de token
@acesso_blueprint.route("/", methods=['GET', 'POST'])
def acesso_token():
    if request.method == 'POST':
        token = request.form.get('token')  # Obtém o token do formulário
        if token:
            return redirect(url_for('acesso.verificar_token', token=token))
        else:
            return render_template("erro.html", mensagem="Por favor, insira um token.")
    return render_template("acesso_token.html")  # Exibe o formulário de entrada de token

# Nova rota para verificar o token
@acesso_blueprint.route("/verificar_token", methods=['GET', 'POST'])
def verificar_token():
    if request.method == 'POST':
        token = request.form.get('token')
        if not token:
            logger.warning("Rota /verificar_token acessada sem o parâmetro 'token'.")
            return render_template("erro.html", mensagem="Por favor, insira um token.")

        conn = None
        try:
            conn = get_mysql_connection()
            cursor = conn.cursor(dictionary=True)
            query_token = "SELECT NUM_NF FROM transporte.nfe_tokens WHERE token = %s"
            params_token = (token,)
            cursor.execute(query_token, params_token)
            result_token = cursor.fetchone()

            if result_token:
                # Token válido, redireciona para a página de rastreio
                return redirect(url_for('acesso.rastreio_token', chave=token))
            else:
                # Token inválido, redireciona para a página de erro
                return render_template("erro.html", mensagem="Token de acesso inválido.")

        except mysql.connector.Error as err:
            logger.error(f"Erro ao verificar token: {err}")
            return render_template("erro.html", mensagem="Erro ao verificar o token.")
        finally:
            if conn and conn.is_connected():
                conn.close()
    else:  # Se for uma requisição GET
        return redirect(url_for('acesso.acesso_token'))  # Redireciona para o formulário

if __name__ == "__main__":
    logger.info("Iniciando aplicação Flask em modo debug.")
    app = Flask(__name__)
    app.register_blueprint(acesso_blueprint)
    app.run(debug=True, port=os.getenv('PORT', 5000))