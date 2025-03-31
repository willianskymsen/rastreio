import logging
import time
import xml.etree.ElementTree as ET
from datetime import datetime

import mysql.connector
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, jsonify, render_template, request

from config import MYSQL_CONFIG
app = Flask(__name__)

# Configuração avançada do logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()
scheduler.start()


# Configuração do MySQL (usando as mesmas configurações do primeiro código)
def get_mysql_connection(max_retries=3, retry_delay=1):
    """Estabelece conexão com o MySQL com retry automático"""
    for attempt in range(max_retries):
        try:
            connection = mysql.connector.connect(
                **MYSQL_CONFIG, autocommit=False, connect_timeout=5, pool_size=5
            )
            if connection.is_connected():
                logger.info(
                    f"Conexão MySQL estabelecida (tentativa {attempt + 1}/{max_retries})"
                )
                return connection
        except mysql.connector.Error as e:
            logger.error(f"Tentativa {attempt + 1} falhou: {str(e)}")
            if attempt == max_retries - 1:
                logger.critical("Falha ao conectar ao MySQL após várias tentativas")
                return None
            time.sleep(retry_delay)
    return None


def fetch_tracking_data(chave_nfe):
    """Faz a requisição à API e retorna os dados processados com base na chave da NF-e."""
    url = "https://ssw.inf.br/api/trackingdanfe"
    data = {"chave_nfe": chave_nfe}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        response = requests.post(url, data=data, headers=headers, timeout=10)
        response.raise_for_status()
        return parse_xml(response.text)
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro na requisição à API: {e}")
        return None


def parse_xml(xml_data):
    """
    Processa o XML de rastreamento e retorna os dados formatados.
    Estrutura esperada:
    <?xml version="1.0" encoding="UTF-8" ?>
    <tracking>
        <success>true</success>
        <message>Documento localizado com sucesso</message>
        <documento>
            <header>...</header>
            <items>...</items>
        </documento>
    </tracking>
    """
    try:
        # Log para diagnóstico (apenas os primeiros 500 caracteres)
        logger.debug(f"Iniciando parse do XML: {xml_data[:500]}...")

        # Parse do XML
        root = ET.fromstring(xml_data)
        
        # 1. Verificação do sucesso da operação
        success = root.find(".//success")
        if success is None:
            logger.error("Tag <success> não encontrada no XML")
            return {
                "status": "ERRO_PROCESSAMENTO",
                "mensagem": "Estrutura XML inválida - tag success não encontrada",
                "items": []
            }
        
        if success.text.lower() != "true":
            message = root.find(".//message")
            error_msg = message.text if message is not None else "Documento não encontrado"
            logger.warning(f"API retornou sucesso=False: {error_msg}")
            return {
                "status": "NAO_ENCONTRADO",
                "mensagem": error_msg,
                "items": []
            }

        # 2. Localização do nó documento
        documento = root.find(".//documento")
        if documento is None:
            logger.error("Tag <documento> não encontrada após sucesso=True")
            return {
                "status": "ERRO_PROCESSAMENTO",
                "mensagem": "Estrutura XML inválida - tag documento não encontrada",
                "items": []
            }

        # 3. Processamento do header
        header = documento.find("header")
        if header is None:
            logger.error("Tag <header> não encontrada dentro de documento")
            return {
                "status": "ERRO_PROCESSAMENTO",
                "mensagem": "Estrutura XML inválida - tag header não encontrada",
                "items": []
            }

        remetente = header.find("remetente").text if header.find("remetente") is not None else ""
        destinatario = header.find("destinatario").text if header.find("destinatario") is not None else ""
        nro_nf = header.find("nro_nf").text if header.find("nro_nf") is not None else ""
        pedido = header.find("pedido").text if header.find("pedido") is not None else ""

        # 4. Processamento dos itens
        items_node = documento.find("items")
        items = []
        
        if items_node is not None:
            for item in items_node.findall("item"):
                try:
                    item_data = {
                        "data_hora": item.find("data_hora").text if item.find("data_hora") is not None else "",
                        "dominio": item.find("dominio").text if item.find("dominio") is not None else "",
                        "filial": item.find("filial").text if item.find("filial") is not None else "",
                        "cidade": item.find("cidade").text if item.find("cidade") is not None else "",
                        "ocorrencia": item.find("ocorrencia").text if item.find("ocorrencia") is not None else "",
                        "descricao": item.find("descricao").text if item.find("descricao") is not None else "",
                        "tipo": item.find("tipo").text if item.find("tipo") is not None else "",
                        "data_hora_efetiva": item.find("data_hora_efetiva").text if item.find("data_hora_efetiva") is not None else "",
                        "nome_recebedor": item.find("nome_recebedor").text if item.find("nome_recebedor") is not None else "",
                        "nro_doc_recebedor": item.find("nro_doc_recebedor").text if item.find("nro_doc_recebedor") is not None else ""
                    }
                    items.append(item_data)
                except Exception as e:
                    logger.warning(f"Erro ao processar item: {str(e)}")
                    continue

        # 5. Determinação do status final
        status_entrega = determinar_status(items) if items else "SEM_EVENTOS"
        
        logger.info(f"XML processado com sucesso - NF: {nro_nf}, Itens: {len(items)}, Status: {status_entrega}")

        # 6. Retorno estruturado
        return {
            "status": "SUCESSO",
            "status_entrega": status_entrega,
            "dados": {
                "remetente": remetente,
                "destinatario": destinatario,
                "NUM_NF": nro_nf,
                "pedido": pedido,
                "items": items
            },
            "mensagem": "Documento processado com sucesso"
        }

    except ET.ParseError as e:
        logger.error(f"Erro ao fazer parse do XML: {str(e)}")
        return {
            "status": "ERRO_PROCESSAMENTO",
            "mensagem": f"Erro ao parsear XML: {str(e)}",
            "items": []
        }
    except Exception as e:
        logger.error(f"Erro inesperado ao processar XML: {str(e)}")
        return {
            "status": "ERRO_PROCESSAMENTO",
            "mensagem": f"Erro inesperado: {str(e)}",
            "items": []
        }


def determinar_status(eventos):
    """Determina o status com base nos eventos da API"""
    if not eventos:
        return "NAO_ENCONTRADO"

    for evento in eventos:
        ocorrencia = evento["ocorrencia"].upper()

        # Verifica se contém "MERCADORIA ENTREGUE" independentemente do código
        if "MERCADORIA ENTREGUE" in ocorrencia:
            return "ENTREGUE"
        # Mantemos as outras verificações como estavam
        if "ENTREGUE" in ocorrencia or "ENTREGA REALIZADA" in ocorrencia:
            return "ENTREGUE"
        if "PROBLEMA" in ocorrencia or "DEVOLVIDO" in ocorrencia:
            return "PROBLEMA"

    return "EM_TRANSITO"


def processar_nfe(chave_nfe, num_nf, transportadora, cidade, uf, dt_saida):
    """Processa NF-e com alimentação sequencial nas tabelas garantindo unicidade de eventos"""
    conn = None
    try:
        # 1. Consulta à API
        dados_api = fetch_tracking_data(chave_nfe)
        conn = get_mysql_connection()
        if not conn:
            logger.error("Falha ao conectar ao MySQL")
            return False

        cursor = conn.cursor()

        # 2. Caso a NF não seja encontrada na API
        if not dados_api or dados_api["status"] != "SUCESSO":
            status = "NAO_ENCONTRADO"
            cursor.execute(
                """
                INSERT INTO nfe_status 
                (chave_nfe, NUM_NF, ultimo_evento, data_hora, status, transportadora, cidade, uf)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    ultimo_evento = VALUES(ultimo_evento),
                    status = VALUES(status),
                    updated_at = CURRENT_TIMESTAMP
                """,
                (chave_nfe, num_nf, "CONSULTA_REALIZADA", dt_saida, status, transportadora, cidade, uf)
            )
            conn.commit()
            logger.info(f"NF-e {num_nf} não encontrada - atualizado status")
            return True

        # 3. Processamento para NF encontrada
        items = dados_api["dados"]["items"]
        status = dados_api["status_entrega"]
        eventos_inseridos = 0

        # 4. Alimentar nfe_logs com verificação de duplicidade
        if items:
            for evento in items:
                try:
                    # Tenta inserir o evento (índice único vai bloquear duplicatas)
                    cursor.execute(
                        """
                        INSERT INTO nfe_logs 
                        (chave_nfe, NUM_NF, evento, data_hora, status, transportadora, cidade, uf)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            chave_nfe,
                            num_nf,
                            evento["ocorrencia"],
                            evento["data_hora"],
                            status,
                            transportadora,
                            cidade,
                            uf
                        )
                    )
                    eventos_inseridos += 1
                except mysql.connector.IntegrityError:
                    # Evento já existe, faz rollback da transação parcial e continua
                    conn.rollback()
                    logger.debug(f"Evento duplicado ignorado: {evento['ocorrencia']} em {evento['data_hora']}")
                    continue
                except Exception as e:
                    logger.error(f"Erro ao inserir log: {evento['ocorrencia']} - {str(e)}")
                    conn.rollback()
                    return False

        # 5. Determinar último evento relevante para atualizar nfe_status
        ultimo_evento = None
        data_ultimo_evento = dt_saida  # Default para DT_SAIDA da NF
        
        if items:
            # Ordena os eventos por data (do mais recente para o mais antigo)
            eventos_ordenados = sorted(items, key=lambda x: x['data_hora'], reverse=True)
            
            # Procura primeiro por evento de entrega
            for evento in eventos_ordenados:
                ocorrencia = evento["ocorrencia"].upper()
                if "MERCADORIA ENTREGUE" in ocorrencia or "ENTREGA REALIZADA" in ocorrencia:
                    ultimo_evento = evento["ocorrencia"]
                    data_ultimo_evento = evento["data_hora"]
                    break
            
            # Se não encontrou entrega, pega o evento mais recente
            if not ultimo_evento:
                ultimo_evento = eventos_ordenados[0]["ocorrencia"]
                data_ultimo_evento = eventos_ordenados[0]["data_hora"]

        # 6. Atualizar nfe_status
        cursor.execute(
            """
            INSERT INTO nfe_status 
            (chave_nfe, NUM_NF, ultimo_evento, data_hora, status, transportadora, cidade, uf)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                ultimo_evento = VALUES(ultimo_evento),
                data_hora = VALUES(data_hora),
                status = VALUES(status),
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                chave_nfe,
                num_nf,
                ultimo_evento if ultimo_evento else "SEM_EVENTOS",
                data_ultimo_evento,
                status,
                transportadora,
                cidade,
                uf
            )
        )

        conn.commit()
        logger.info(
            f"NF-e {num_nf} processada. Status: {status}, "
            f"Novos eventos inseridos: {eventos_inseridos}/{len(items)}"
        )
        return True

    except Exception as e:
        logger.error(f"Erro crítico ao processar NF-e {num_nf}: {str(e)}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn and conn.is_connected():
            conn.close()


def buscar_e_processar_nfes():
    """Tarefa agendada para buscar e processar NF-es não entregues"""
    logger.info("Iniciando processamento de NF-es não entregues")
    conn = None
    try:
        conn = get_mysql_connection()
        if not conn:
            logger.error("Falha ao conectar ao MySQL")
            return

        with conn.cursor(dictionary=True) as cursor:
            # Busca apenas NF-es não entregues ou com status indefinido
            cursor.execute("""
                SELECT 
                    n.CHAVE_ACESSO_NFEL, 
                    n.NUM_NF, 
                    n.NOME_TRP as transportadora, 
                    n.CIDADE, 
                    n.UF,
                    n.DT_SAIDA,
                    s.status as status_atual
                FROM nfe n
                JOIN transportadoras t ON n.NOME_TRP = t.DESCRICAO
                LEFT JOIN nfe_status s ON n.CHAVE_ACESSO_NFEL = s.chave_nfe
                WHERE t.SISTEMA = 'SSW'
                AND (
                    s.chave_nfe IS NULL  -- NFe nunca consultada
                    OR (
                        s.status IN ('EM_TRANSITO', 'NAO_ENCONTRADO', 'SEM_EVENTOS')
                        AND s.updated_at < DATE_SUB(NOW(), INTERVAL 24 HOUR)
                    )
                )
                ORDER BY 
                    CASE 
                        WHEN s.status IS NULL THEN 0  -- Prioridade para NFe nunca consultadas
                        WHEN s.status = 'NAO_ENCONTRADO' THEN 1
                        WHEN s.status = 'EM_TRANSITO' THEN 2
                        ELSE 3
                    END,
                    s.updated_at ASC  -- As mais antigas primeiro
                LIMIT 100  -- Limite para evitar sobrecarga
            """)

            nfes = cursor.fetchall()
            if not nfes:
                logger.info("Nenhuma NF-e não entregue encontrada para processar")
                return

            total_nfes = len(nfes)
            logger.info(f"Total de NF-es não entregues a processar: {total_nfes}")

            for idx, nfe in enumerate(nfes, 1):
                try:
                    logger.info(f"Processando NF-e {idx}/{total_nfes}: {nfe['NUM_NF']} (Status atual: {nfe.get('status_atual', 'NOVO')}")
                    
                    success = processar_nfe(
                        chave_nfe=nfe["CHAVE_ACESSO_NFEL"],
                        num_nf=nfe["NUM_NF"],
                        transportadora=nfe["transportadora"],
                        cidade=nfe["CIDADE"],
                        uf=nfe["UF"],
                        dt_saida=nfe["DT_SAIDA"]
                    )
                    if not success:
                        logger.warning(f"Falha ao processar NF-e {nfe['NUM_NF']}")
                except Exception as e:
                    logger.error(f"Erro ao processar NF-e {nfe['NUM_NF']}: {str(e)}")
                    continue

            logger.info(f"Processamento concluído. Total de NF-es não entregues processadas: {total_nfes}")

    except Exception as e:
        logger.error(f"Erro no processamento automático: {str(e)}")
    finally:
        if conn and conn.is_connected():
            conn.close()


# Agendando a tarefa para rodar a cada 5 minutos
scheduler.add_job(
    buscar_e_processar_nfes,
    "interval",
    minutes=5,
    next_run_time=datetime.now(),  # Executa imediatamente ao iniciar
)


@app.route("/")
def index():
    return render_template("index2.html")


@app.route("/api/arquivos", methods=["GET"])
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
        
        app.logger.info(f"NFs encontradas: {len(nfes)}")
        
        return jsonify(nfes)

    except Exception as e:
        logger.error(f"Erro ao buscar arquivos: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/dados", methods=["POST"])
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

@app.route("/api/status", methods=["GET"])
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


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
