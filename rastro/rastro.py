from flask import Blueprint, render_template, request, jsonify
from modules.database import get_mysql_connection
from modules.tracking import fetch_tracking_data
from modules.logger_config import logger
from modules.tasks import processar_nfe
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

        with conn.cursor(dictionary=True) as cursor:
            # 1. Verifica se a NF existe e pertence a transportadora SSW
            cursor.execute(
                """
                SELECT n.CHAVE_ACESSO_NFEL, n.NOME_TRP as transportadora, n.CIDADE, n.UF, n.DT_SAIDA
                FROM nfe n
                JOIN transportadoras t ON n.NOME_TRP = t.DESCRICAO
                WHERE n.NUM_NF = %s 
                AND t.SISTEMA = 'SSW'
                LIMIT 1
            """,
                (num_nf,),
            )

            nfe = cursor.fetchone()
            if not nfe:
                return jsonify(
                    {
                        "error": "NF-e não encontrada ou não pertence a transportadora SSW",
                        "details": f"NF-e {num_nf} não existe ou não é rastreável",
                    }
                ), 404

            chave_nfe = nfe["CHAVE_ACESSO_NFEL"]
            transportadora = nfe["transportadora"]
            cidade = nfe["CIDADE"]
            uf = nfe["UF"]
            dt_saida = nfe["DT_SAIDA"]

            # 2. Consulta a API SSW
            dados_api = fetch_tracking_data(chave_nfe)
            if not dados_api:
                return jsonify(
                    {
                        "error": "Não foi possível obter dados de rastreamento",
                        "details": "Falha ao consultar a API de rastreamento",
                    }
                ), 502

            # 3. Processa a NF-e
            success = processar_nfe(chave_nfe, num_nf, transportadora, cidade, uf, dt_saida)
            if not success:
                return jsonify(
                    {
                        "error": "Erro ao salvar dados no banco",
                        "details": "Falha ao processar os dados de rastreamento",
                    }
                ), 500

            return jsonify(dados_api)

    except mysql.connector.Error as db_error:
        logger.error(f"Erro de banco de dados: {db_error}")
        if conn:
            conn.rollback()
        return jsonify(
            {"error": "Erro ao processar no banco de dados", "details": str(db_error)}
        ), 500
    except Exception as e:
        logger.error(f"Erro inesperado: {e}")
        if conn:
            conn.rollback()
        return jsonify({"error": "Erro interno no servidor", "details": str(e)}), 500
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