from flask import Blueprint, render_template, request, jsonify
from modules.database import get_mysql_connection
from modules.logger_config import logger
import mysql.connector

rastro_blueprint = Blueprint('rastro', __name__, template_folder='templates', static_folder='static')

@rastro_blueprint.route("/")
def index():
    return render_template("index.html")


@rastro_blueprint.route("/rastro/api/arquivos", methods=["GET"])
def api_arquivos():
    try:
        # Obter parâmetro de filtro da query string
        status_filter = request.args.get('status', '').upper()
        
        conn = get_mysql_connection()
        if not conn:
            return jsonify({"error": "Falha na conexão com o MySQL"}), 500

        cursor = conn.cursor(dictionary=True)
        
        # Consulta base
        query = """
            SELECT 
                NUM_NF,
                status,
                transportadora,
                cidade,
                uf
            FROM nfe_status
            WHERE NUM_NF IS NOT NULL
            AND NUM_NF != ''
        """
        
        # Adicionar filtro de status se fornecido
        params = []
        if status_filter in ['ENTREGUE', 'EM_TRANSITO']:
            query += " AND status = %s"
            params.append(status_filter)
        elif status_filter:
            # Se fornecido um filtro inválido, retornar vazio
            return jsonify([])
            
        query += " ORDER BY updated_at DESC"
        
        cursor.execute(query, params)
        nfes = cursor.fetchall()
        conn.close()
        
        logger.info(f"NFs encontradas: {len(nfes)}")
        
        return jsonify(nfes)

    except Exception as e:
        logger.error(f"Erro ao buscar arquivos: {str(e)}")
        return jsonify({"error": str(e)}), 500


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
    try:
        conn = get_mysql_connection()
        if not conn:
            return jsonify({"error": "Falha na conexão com o MySQL"}), 500

        with conn.cursor(dictionary=True) as cursor:
            # Filtra apenas os status relevantes
            cursor.execute("""
                SELECT 
                    status,
                    COUNT(*) as count
                FROM nfe_status
                WHERE status IN ('ENTREGUE', 'EM_TRANSITO')
                GROUP BY status
            """)

            status_counts = cursor.fetchall()
            
            result = {
                'ENTREGUE': 0,
                'EM_TRANSITO': 0,
                'TOTAL': 0
            }
            
            for item in status_counts:
                status = item['status']
                if status in result:
                    result[status] = item['count']
                result['TOTAL'] += item['count']

            return jsonify(result)

    except Exception as e:
        logger.error(f"Erro ao buscar status: {str(e)}")
        return jsonify({"error": "Erro ao buscar status"}), 500
    finally:
        if conn and conn.is_connected():
            conn.close()