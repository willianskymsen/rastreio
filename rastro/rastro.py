from flask import Blueprint, render_template, request, jsonify
from modules.database import get_mysql_connection
from modules.logger_config import logger
from modules import status
import mysql.connector

rastro_blueprint = Blueprint('rastro', __name__, template_folder='templates', static_folder='static')

@rastro_blueprint.route("/")
def index():
    return render_template("index.html")


@rastro_blueprint.route("/rastro/api/arquivos", methods=["GET"])
def api_arquivos():
    # ... (seu código atual para api_arquivos - manter inalterado)
    try:
        # Obter parâmetro de filtro da query string
        status_filter = request.args.get('status', '').upper()

        conn = get_mysql_connection()
        if not conn:
            return jsonify({"error": "Falha na conexão com o MySQL"}), 500

        cursor_nfe_status = conn.cursor(dictionary=True)

        # Consulta base para obter as NFs, incluindo a coluna ultimo_evento
        query_nfes = """
            SELECT
                NUM_NF,
                transportadora,
                cidade,
                uf,
                ultimo_evento
            FROM nfe_status
            WHERE NUM_NF IS NOT NULL
            AND NUM_NF != ''
            ORDER BY updated_at DESC
        """
        cursor_nfe_status.execute(query_nfes)
        nfes_data = cursor_nfe_status.fetchall()

        nfes_com_status_determinado = []

        for nfe in nfes_data:
            ultimo_evento = nfe.get('ultimo_evento')

            # Determinar o status usando o módulo status
            status_determinado = status.determinar_status(conn, ultimo_evento)

            # Adicionar o status determinado ao dicionário da NF
            nfe['status'] = status_determinado
            nfes_com_status_determinado.append(nfe)

        conn.close()

        # Filtrar as NFs com base no parâmetro de status (agora no status determinado)
        nfes_filtradas = []
        if status_filter in ['ENTREGUE', 'PROBLEMA', 'EM_TRANSITO', 'NAO_ENCONTRADO']:
            for nfe in nfes_com_status_determinado:
                if nfe['status'] == status_filter:
                    nfes_filtradas.append(nfe)
        elif not status_filter:
            nfes_filtradas = nfes_com_status_determinado
        else:
            return jsonify([]) # Retorna vazio se o filtro de status for inválido

        logger.info(f"NFs encontradas após determinação de status: {len(nfes_filtradas)}")

        return jsonify(nfes_filtradas)

    except Exception as e:
        logger.error(f"Erro ao buscar arquivos: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()

@rastro_blueprint.route("/rastro/api/dados", methods=["POST"])
def api_dados():
    conn = None
    try:
        num_nf = request.json.get("filename")
        if not num_nf:
            return jsonify({"error": "Número da NF não fornecido"}), 400

        conn = get_mysql_connection()
        if not conn:
            return jsonify({"error": "Falha na conexão com o MySQL"}), 500

        response_data = {}

        # Buscar histórico de rastreamento da tabela nfe_logs
        with conn.cursor(dictionary=True) as cursor_logs:
            cursor_logs.execute(
                """
                SELECT
                    codigo_ocorrencia,
                    tipo_ocorrencia,
                    descricao_completa,
                    data_hora,
                    status,
                    cidade_ocorrencia,
                    uf,
                    dominio,
                    filial,
                    nome_recebedor,
                    documento_recebedor
                FROM nfe_logs
                WHERE NUM_NF = %s
                ORDER BY data_hora DESC
                """,
                (num_nf,),
            )
            response_data['historico_rastreamento'] = cursor_logs.fetchall()

        # Buscar informações adicionais da tabela nfe
        with conn.cursor(dictionary=True) as cursor_nfe:
            cursor_nfe.execute(
                """
                SELECT NOME, PESO_BRT, QTD_VOLUMES
                FROM nfe
                WHERE NUM_NF = %s
                LIMIT 1
                """,
                (num_nf,),
            )
            nfe_info = cursor_nfe.fetchone()
            if nfe_info:
                response_data['destinatario'] = nfe_info.get('NOME')
                response_data['peso'] = nfe_info.get('PESO_BRT')
                response_data['volumes'] = nfe_info.get('QTD_VOLUMES')

        conn.close()

        logger.info(f"Dados de rastreamento e informações da NF {num_nf} buscados com sucesso.")
        return jsonify(response_data)

    except mysql.connector.Error as db_error:
        logger.error(f"Erro de banco de dados ao buscar dados: {db_error}")
        if conn:
            conn.rollback()
        return jsonify(
            {"error": "Erro ao buscar dados no banco de dados", "details": str(db_error)}
        ), 500
    except Exception as e:
        logger.error(f"Erro inesperado ao buscar dados: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Erro interno ao buscar dados", "details": str(e)}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()

@rastro_blueprint.route("/rastro/api/status", methods=["GET"])
def api_status():
    conn = None
    try:
        conn = get_mysql_connection()
        if not conn:
            return jsonify({"error": "Falha na conexão com o MySQL"}), 500

        cursor_nfe_status = conn.cursor(dictionary=True)

        # Buscar todos os registros de nfe_status para obter o ultimo_evento
        cursor_nfe_status.execute("SELECT NUM_NF, ultimo_evento FROM nfe_status WHERE NUM_NF IS NOT NULL AND NUM_NF != ''")
        nfe_status_data = cursor_nfe_status.fetchall()

        status_counts = {
            'ENTREGUE': 0,
            'EM_TRANSITO': 0,
            'PROBLEMA': 0,
            'NAO_ENCONTRADO': 0,
            'TOTAL': 0
        }

        for item in nfe_status_data:
            ultimo_evento = item.get('ultimo_evento')

            # Determinar o status usando o módulo status
            status_determinado = status.determinar_status(conn, ultimo_evento)
            status_counts[status_determinado] += 1
            status_counts['TOTAL'] += 1

        conn.close()
        return jsonify(status_counts)

    except Exception as e:
        logger.error(f"Erro ao buscar status: {str(e)}")
        return jsonify({"error": "Erro ao buscar status"}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()