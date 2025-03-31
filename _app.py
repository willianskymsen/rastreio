import logging
import socket
import time
import traceback
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from functools import lru_cache
from threading import Lock, Thread

import cx_Oracle
import mysql.connector
import pytz
import requests
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
from ratelimit import limits, sleep_and_retry
from tenacity import retry, stop_after_attempt, wait_exponential

from config import MYSQL_CONFIG, ORACLE_PASSWORD, ORACLE_SERVICE_NAME, ORACLE_USER

load_dotenv()

app = Flask(__name__)
app_start_time = time.time()
CORS(app)

# Configuração avançada do logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuração do scheduler com persistência
scheduler = BackgroundScheduler(
    jobstores={
        'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
    },
    timezone="America/Sao_Paulo",
    misfire_grace_time=3600
)

print("Timezone:", time.tzname)
print("Horário atual:", datetime.now(pytz.timezone('America/Sao_Paulo')))

# Variáveis globais
app.inicializado = False
ultima_importacao = None
ultima_consulta_api = None
ultima_atualizacao_categorias = None
import_lock = Lock()  # Lock para evitar concorrência

# Métricas atualizadas
api_metrics = {
    'total_requests': 0,
    'successful_requests': 0,
    'failed_requests': 0,
    'timeout_errors': 0,
    'average_response_time': 0
}

# --- FUNÇÕES DE CONEXÃO COM BANCOS ---
def get_db_connection():
    """Retorna uma conexão com o banco Oracle com tratamento robusto de erros"""
    try:
        connection = cx_Oracle.connect(
            user=ORACLE_USER,
            password=ORACLE_PASSWORD,
            dsn=ORACLE_SERVICE_NAME,
            encoding="UTF-8",
            nencoding="UTF-8"
        )
        logger.info("Conexão Oracle estabelecida com sucesso")
        return connection
    except cx_Oracle.Error as e:
        logger.error(f"Erro ao conectar ao Oracle: {str(e)}")
        return None

def get_mysql_connection(max_retries=3, retry_delay=1):
    """Estabelece conexão com o MySQL com retry automático"""
    for attempt in range(max_retries):
        try:
            connection = mysql.connector.connect(
                **MYSQL_CONFIG,
                autocommit=False,
                connect_timeout=5,
                pool_size=5
            )
            if connection.is_connected():
                logger.info(f"Conexão MySQL estabelecida (tentativa {attempt+1}/{max_retries})")
                return connection
        except mysql.connector.Error as e:
            logger.error(f"Tentativa {attempt+1} falhou: {str(e)}")
            if attempt == max_retries - 1:
                logger.critical("Falha ao conectar ao MySQL após várias tentativas")
                return None
            time.sleep(retry_delay)
    return None

# --- FUNÇÕES PRINCIPAIS ---
def verificar_tabelas():
    """Verifica se todas as tabelas necessárias existem no MySQL"""
    required_tables = ['nfe', 'nfe_status', 'nfe_logs', 'nfe_categorias', 'transportadoras']
    missing_tables = []
    
    with get_mysql_connection() as conn:
        if not conn:
            raise RuntimeError("Não foi possível conectar ao MySQL para verificar tabelas")
        
        cursor = conn.cursor()
        for table in required_tables:
            cursor.execute(f"SHOW TABLES LIKE '{table}'")
            if not cursor.fetchone():
                missing_tables.append(table)
    
    if missing_tables:
        raise RuntimeError(f"Tabelas faltando no MySQL: {', '.join(missing_tables)}")
    else:
        logger.info("Todas as tabelas necessárias existem no MySQL")

def executar_importacao_nfes(importar_todas=False):
    """Importa NFes do Oracle para o MySQL com tratamento completo"""
    global ultima_importacao
    
    with import_lock:  # Garante que apenas uma importação ocorra por vez
        oracle_conn = get_db_connection()
        mysql_conn = get_mysql_connection()

        if not oracle_conn or not mysql_conn:
            logger.error("Falha ao conectar a um dos bancos de dados")
            return 0

        try:
            with oracle_conn.cursor() as oracle_cursor, \
                 mysql_conn.cursor() as mysql_cursor:

                # Filtro para pegar apenas registros novos
                filtro_data = ""
                if not importar_todas:
                    try:
                        mysql_cursor.execute("SELECT MAX(DT_SAIDA), MAX(NUM_NF) FROM nfe")
                        ultima_data, ultimo_num_nf = mysql_cursor.fetchone()
                        
                        if ultima_data is not None:  # Só adiciona filtro se houver dados
                            # Converter para string no formato Oracle
                            data_str = ultima_data.strftime('%Y-%m-%d %H:%M:%S')
                            filtro_data = f"""
                                AND (DT_SAIDA > TO_TIMESTAMP('{data_str}', 'YYYY-MM-DD HH24:MI:SS')
                                    OR (DT_SAIDA = TO_TIMESTAMP('{data_str}', 'YYYY-MM-DD HH24:MI:SS') 
                                        AND NUM_NF > {ultimo_num_nf or 0}))
                            """
                            logger.info(f"Importando apenas NFes após {data_str}")
                        else:
                            logger.info("Nenhum registro encontrado no MySQL - importando todos")
                    except Exception as e:
                        logger.error(f"Erro ao verificar última data: {str(e)}")
                        importar_todas = True  # Fallback para importar tudo

                # Consulta otimizada ao Oracle com tratamento robusto de datas
                query = f"""
                    SELECT 
                        NUM_NF, 
                        TO_CHAR(DT_SAIDA, 'YYYY-MM-DD HH24:MI:SS') as DT_SAIDA,
                        CLI_ID,
                        NOME, 
                        CIDADE, 
                        UF, 
                        VLR_TOTAL,
                        FORN_ID,
                        NOME_TRP, 
                        CHAVE_ACESSO_NFEL
                    FROM FOCCO3I.TNFS_SAIDA
                    WHERE DT_CANC IS NULL
                    AND TP_FRETE = 'C'
                    {filtro_data}
                    ORDER BY DT_SAIDA
                """
                
                logger.info(f"Executando query no Oracle: {query[:200]}...")
                
                try:
                    oracle_cursor.execute(query)
                    total_importados = 0
                    
                    for row in oracle_cursor:
                        try:
                            # Conversão de tipos segura
                            num_nf = int(row[0]) if row[0] else None
                            dt_saida = row[1].split('.')[0] if row[1] else None  # Remove milissegundos
                            cli_id = int(row[2]) if row[2] else None
                            vlr_total = float(row[6]) if row[6] else 0.0
                            forn_id = int(row[7]) if row[7] else None

                            # Inserção no MySQL
                            mysql_cursor.execute("""
                                INSERT INTO nfe (
                                    NUM_NF, DT_SAIDA, CLI_ID, NOME_CLIENTE, 
                                    CIDADE, UF, VLR_TOTAL, FORN_ID,
                                    NOME_TRP, CHAVE_ACESSO_NFEL
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON DUPLICATE KEY UPDATE
                                    DT_SAIDA = VALUES(DT_SAIDA),
                                    NOME_CLIENTE = VALUES(NOME_CLIENTE),
                                    CIDADE = VALUES(CIDADE),
                                    UF = VALUES(UF),
                                    VLR_TOTAL = VALUES(VLR_TOTAL),
                                    updated_at = NOW()
                            """, (
                                num_nf, dt_saida, cli_id, row[3], 
                                row[4], row[5], vlr_total, forn_id, 
                                row[8], row[9]
                            ))

                            total_importados += 1
                            
                        except Exception as e:
                            logger.error(f"Erro ao importar NFe {row[0]}: {str(e)}")
                            continue

                    mysql_conn.commit()
                    ultima_importacao = datetime.now()
                    logger.info(f"Importação concluída - {total_importados} registros processados")
                    return total_importados

                except cx_Oracle.DatabaseError as e:
                    error, = e.args
                    logger.error(f"Erro Oracle (código {error.code}): {error.message}")
                    logger.error(f"Query completa: {query}")
                    return 0
                
        except Exception as e:
            logger.error(f"Erro crítico na importação: {str(e)}")
            logger.error(traceback.format_exc())
            return 0
        finally:
            if oracle_conn:
                oracle_conn.close()
            if mysql_conn and mysql_conn.is_connected():
                mysql_conn.close()

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def fetch_tracking_data(chave_nfe):
    """Consulta a API de rastreamento com tratamento robusto de erros"""
    global api_metrics
    
    url = "https://ssw.inf.br/api/trackingdanfe"
    data = {'chave_nfe': chave_nfe}
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    
    start_time = time.time()
    api_metrics['total_requests'] += 1
    
    try:
        response = requests.post(url, data=data, headers=headers, timeout=10)
        response_time = time.time() - start_time
        
        # Atualiza métricas
        api_metrics['average_response_time'] = (
            (api_metrics['average_response_time'] * api_metrics['successful_requests'] + response_time) / 
            (api_metrics['successful_requests'] + 1))
        
        if response.status_code != 200:
            logger.error(f"Erro na API: HTTP {response.status_code}")
            api_metrics['failed_requests'] += 1
            return None
            
        api_metrics['successful_requests'] += 1
        return parse_xml(response.text)
        
    except requests.exceptions.Timeout:
        logger.error("Timeout na consulta à API SSW")
        api_metrics['timeout_errors'] += 1
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"Erro na requisição: {str(e)}")
        api_metrics['failed_requests'] += 1
        return None

def parse_xml(xml_data):
    """Parse do XML com validação robusta"""
    try:
        root = ET.fromstring(xml_data)
        
        # Verifica se a consulta foi bem-sucedida
        success = root.find(".//success")
        if success is None or success.text.lower() != "true":
            logger.warning("API retornou success=False")
            return None

        # Extrai dados do header
        header = root.find(".//header")
        if header is None:
            logger.warning("Nenhum header encontrado no XML")
            return None
            
        items = []
        for item in root.findall(".//item"):
            try:
                item_data = {
                    "data_hora": item.find("data_hora").text if item.find("data_hora") is not None else "",
                    "ocorrencia": item.find("ocorrencia").text if item.find("ocorrencia") is not None else "",
                    "descricao": item.find("descricao").text if item.find("descricao") is not None else "",
                    "tipo": item.find("tipo").text if item.find("tipo") is not None else "",
                    "nome_recebedor": item.find("nome_recebedor").text if item.find("nome_recebedor") is not None else ""
                }
                items.append(item_data)
            except AttributeError as e:
                logger.warning(f"Erro ao parsear item: {str(e)}")
                continue

        return {
            "destinatario": header.find("destinatario").text if header.find("destinatario") is not None else "",
            "nNF": header.find("nro_nf").text if header.find("nro_nf") is not None else "",
            "items": items
        }

    except ET.ParseError as e:
        logger.error(f"Erro ao parsear XML: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Erro inesperado no parse: {str(e)}")
        return None

def determinar_status(eventos):
    """Determina o status da NFe com base nos eventos"""
    if not eventos or len(eventos) == 0:
        return "NAO_EXPEDIDO"
    
    for evento in eventos:
        if isinstance(evento, dict) and 'ocorrencia' in evento:
            ocorrencia = evento['ocorrencia'].lower()
            if 'entregue' in ocorrencia or 'entrega realizada' in ocorrencia:
                return "ENTREGUE"
    
    for evento in eventos:
        if isinstance(evento, dict) and 'ocorrencia' in evento:
            ocorrencia = evento['ocorrencia'].lower()
            if ('em trânsito' in ocorrencia or 
                'a caminho' in ocorrencia or 
                'rota de entrega' in ocorrencia):
                return "TRANSITO"
    
    return "NAO_EXPEDIDO"

def atualizar_status_nfe(chave_nfe, dados_api):
    """Atualiza o status de uma NFe no banco de dados"""
    if not dados_api or not dados_api.get('items'):
        logger.warning(f"Nenhum dado válido para atualizar chave {chave_nfe}")
        return False

    status = determinar_status(dados_api['items'])
    with get_mysql_connection() as conn:
        if not conn:
            return False
            
        try:
            cursor = conn.cursor()
            
            # Atualiza o status principal
            cursor.execute("""
                INSERT INTO nfe_status (chave_nfe, ultimo_evento, data_hora, status)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    ultimo_evento = VALUES(ultimo_evento),
                    data_hora = VALUES(data_hora),
                    status = VALUES(status),
                    updated_at = NOW()
            """, (
                chave_nfe,
                dados_api['items'][0]['ocorrencia'],
                dados_api['items'][0]['data_hora'],
                status
            ))
            
            # Insere no log de eventos
            for item in dados_api['items']:
                cursor.execute("""
                    INSERT INTO nfe_logs (chave_nfe, evento, data_hora, status)
                    VALUES (%s, %s, %s, %s)
                """, (
                    chave_nfe,
                    item['ocorrencia'],
                    item['data_hora'],
                    status
                ))
            
            conn.commit()
            logger.info(f"Status atualizado para chave {chave_nfe}: {status}")
            return True
            
        except mysql.connector.Error as e:
            logger.error(f"Erro ao atualizar status no MySQL: {str(e)}")
            conn.rollback()
            return False

class NFeTracker:
    def __init__(self):
        self.first_run = True
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/x-www-form-urlencoded'})

    @sleep_and_retry
    @limits(calls=100, period=1)
    def fetch_with_rate_limit(self, chave_nfe):
        """Consulta a API com rate limiting"""
        try:
            response = self.session.post(
                "https://ssw.inf.br/api/trackingdanfe",
                data={'chave_nfe': chave_nfe},
                timeout=10
            )
            return parse_xml(response.text) if response.status_code == 200 else None
        except Exception as e:
            logger.error(f"Erro na requisição para {chave_nfe[:10]}...: {str(e)}")
            return None

    def consulta_api_automatica(self):
        """Consulta automática com controle inteligente por status e tempo"""
        global ultima_consulta_api
        
        logger.info("Iniciando consulta API automática")
        start_time = time.time()
        total_atualizadas = 0
        
        try:
            with get_mysql_connection() as conn:
                if not conn:
                    return False
                
                cursor = conn.cursor(dictionary=True)
                
                # Query para selecionar chaves que precisam ser verificadas
                query = """
                    SELECT 
                        n.CHAVE_ACESSO_NFEL,
                        n.NUM_NF,
                        n.NOME_TRP as transportadora,
                        n.CIDADE,
                        n.UF,
                        s.status,
                        MAX(l.data_hora) as ultima_verificacao
                    FROM nfe n
                    LEFT JOIN nfe_status s ON n.CHAVE_ACESSO_NFEL = s.chave_nfe
                    LEFT JOIN nfe_logs l ON n.CHAVE_ACESSO_NFEL = l.chave_nfe
                    WHERE n.CHAVE_ACESSO_NFEL IS NOT NULL
                    AND LENGTH(TRIM(n.CHAVE_ACESSO_NFEL)) = 44
                    AND (
                        /* Novas chaves sem registro de status */
                        s.status IS NULL 
                        /* Ou em transito com última verificação há mais de 24 horas */
                        OR (s.status = 'TRANSITO' AND (
                            l.data_hora IS NULL 
                            OR l.data_hora < DATE_SUB(NOW(), INTERVAL 24 HOUR)
                        )
                        /* Ou chaves sem nenhum log (primeira verificação) */
                        OR NOT EXISTS (
                            SELECT 1 FROM nfe_logs 
                            WHERE chave_nfe = n.CHAVE_ACESSO_NFEL
                        )
                    )
                    AND n.DT_SAIDA > DATE_SUB(NOW(), INTERVAL 30 DAY)
                    GROUP BY n.CHAVE_ACESSO_NFEL, n.NUM_NF, n.NOME_TRP, n.CIDADE, n.UF, s.status
                    ORDER BY 
                        CASE 
                            WHEN s.status IS NULL THEN 0  -- Prioridade máxima para novas
                            ELSE 1                       -- Depois as em trânsito
                        END,
                        n.DT_SAIDA DESC
                    LIMIT 100  -- Limite de 100 chaves por execução
                """
                
                cursor.execute(query)
                chaves = cursor.fetchall()
                
                if not chaves:
                    logger.info("Nenhuma NFe necessita atualização neste ciclo")
                    return True
                
                logger.info(f"Processando {len(chaves)} NFes para atualização")
                
                # Processamento com rate limiting (5 minutos para 100 chaves = ~1 chave a cada 3 segundos)
                with ThreadPoolExecutor(max_workers=5) as executor:
                    futures = []
                    for i, nfe in enumerate(chaves):
                        # Espaça as requisições em ~3 segundos para 100 chaves em 5 minutos
                        if i > 0:
                            time.sleep(3)
                        
                        futures.append(
                            executor.submit(
                                self.processar_nfe_completa,
                                nfe['CHAVE_ACESSO_NFEL'],
                                nfe['NUM_NF'],
                                nfe['transportadora'],
                                nfe['CIDADE'],
                                nfe['UF']
                            )
                        )
                    
                    for future in as_completed(futures):
                        if future.result():
                            total_atualizadas += 1
                
                elapsed = time.time() - start_time
                logger.info(f"Concluído: {total_atualizadas} NFes atualizadas em {elapsed:.2f}s")
                ultima_consulta_api = datetime.now()
                return True
                
        except Exception as e:
            logger.error(f"Erro na consulta automática: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    def processar_nfe_completa(self, chave_nfe, num_nf, transportadora, cidade, uf):
        """Versão otimizada do processamento individual"""
        try:
            dados_api = self.fetch_with_rate_limit(chave_nfe)
            if not dados_api or not dados_api.get('items'):
                return False
            
            status = determinar_status(dados_api['items'])
            ultimo_evento = dados_api['items'][0]
            
            with get_mysql_connection() as conn:
                if not conn:
                    return False
                
                cursor = conn.cursor()
                
                # Atualização otimizada
                cursor.execute("""
                    INSERT INTO nfe_status (
                        chave_nfe, NUM_NF, ultimo_evento, data_hora, 
                        status, transportadora, cidade, uf, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    ON DUPLICATE KEY UPDATE
                        ultimo_evento = VALUES(ultimo_evento),
                        data_hora = VALUES(data_hora),
                        status = VALUES(status),
                        updated_at = NOW()
                """, (
                    chave_nfe, num_nf, ultimo_evento['ocorrencia'],
                    ultimo_evento['data_hora'], status,
                    transportadora, cidade, uf
                ))
                
                # Bulk insert para os logs
                log_values = [
                    (chave_nfe, num_nf, item['ocorrencia'],
                     item['data_hora'], status,
                     transportadora, cidade, uf)
                    for item in dados_api['items']
                ]
                
                cursor.executemany("""
                    INSERT IGNORE INTO nfe_logs (
                        chave_nfe, NUM_NF, evento, data_hora,
                        status, transportadora, cidade, uf
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, log_values)
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Erro ao processar {chave_nfe[:10]}...: {str(e)}")
            return False

# Inicialização do tracker
nfe_tracker = NFeTracker()

def atualizar_categorias():
    """Atualiza as estatísticas de categorias no MySQL"""
    global ultima_atualizacao_categorias
    
    with get_mysql_connection() as conn:
        if not conn:
            return False
            
        try:
            cursor = conn.cursor()
            
            # Atualiza estatísticas por transportadora
            cursor.execute("""
                INSERT INTO nfe_categorias (data, transportadora_id, entregue, transito, nao_expedido)
                SELECT 
                    NOW(),
                    t.id,
                    SUM(CASE WHEN s.status = 'ENTREGUE' THEN 1 ELSE 0 END),
                    SUM(CASE WHEN s.status = 'TRANSITO' THEN 1 ELSE 0 END),
                    SUM(CASE WHEN s.status = 'NAO_EXPEDIDO' OR s.status IS NULL THEN 1 ELSE 0 END)
                FROM transportadoras t
                LEFT JOIN nfe n ON t.id = n.transportadora_id
                LEFT JOIN nfe_status s ON n.CHAVE_ACESSO_NFEL = s.chave_nfe
                GROUP BY t.id
                ON DUPLICATE KEY UPDATE
                    data = VALUES(data),
                    entregue = VALUES(entregue),
                    transito = VALUES(transito),
                    nao_expedido = VALUES(nao_expedido)
            """)
            
            conn.commit()
            ultima_atualizacao_categorias = datetime.now()
            logger.info("Estatísticas de categorias atualizadas")
            return True
            
        except mysql.connector.Error as e:
            logger.error(f"Erro ao atualizar categorias: {str(e)}")
            return False

# --- FUNÇÕES AGENDADAS ---
def importacao_automatica():
    """Tarefa agendada para importação de NFes"""
    logger.info("Iniciando importação automática de NFes")
    try:
        total = executar_importacao_nfes()
        logger.info(f"Importação automática concluída - {total} registros")
    except Exception as e:
        logger.error(f"Falha na importação automática: {str(e)}")

def consulta_api_automatica():
    """Tarefa agendada para consulta à API"""
    return nfe_tracker.consulta_api_automatica()

def atualizar_estatisticas_automatico():
    """Tarefa agendada para atualizar estatísticas"""
    logger.info("Iniciando atualização automática de estatísticas")
    try:
        atualizar_categorias()
    except Exception as e:
        logger.error(f"Falha ao atualizar estatísticas: {str(e)}")

# --- CONFIGURAÇÃO DO SCHEDULER ---
def configurar_agendadores():
    """Configura todas as tarefas periódicas"""
    try:
        scheduler.remove_all_jobs()
        
        # Importação a cada 3 horas
        scheduler.add_job(
            importacao_automatica,
            'interval',
            hours=3,
            next_run_time=datetime.now(),
            id='importacao_nfes'
        )
        
        # Consulta API a cada 3 horas (com offset de 30 minutos)
        scheduler.add_job(
            consulta_api_automatica,
            'interval',
            minutes=5,  # Executa a cada 5 minutos
            id='consulta_api_automatica',
            max_instances=1  # Garante que não execute em paralelo
        )
        
        # Atualização de estatísticas a cada 3 horas (com offset de 60 minutos)
        scheduler.add_job(
            atualizar_estatisticas_automatico,
            'interval',
            hours=3,
            next_run_time=datetime.now() + timedelta(minutes=60),
            id='atualizar_estatisticas'
        )
        
        logger.info("Agendadores configurados com sucesso")
    except Exception as e:
        logger.error(f"Erro ao configurar agendadores: {str(e)}")
        raise

# --- INICIALIZAÇÃO ---
def inicializar_aplicacao():
    """Executa todas as operações necessárias ao iniciar o servidor"""
    global app
    
    if app.inicializado:
        logger.info("Aplicação já inicializada")
        return True

    logger.info("Iniciando rotina de inicialização")
    
    try:
        # 1. Verificar tabelas
        verificar_tabelas()
        
        # 2. Iniciar scheduler
        if not scheduler.running:
            scheduler.start()
            logger.info("Scheduler iniciado")
        
        # 3. Configurar agendadores
        configurar_agendadores()
        
        # 4. Executar primeira importação (com lock para evitar concorrência)
        with import_lock:
            logger.info("Executando primeira importação")
            executar_importacao_nfes(importar_todas=True)
        
        # 5. Status final
        app.inicializado = True
        logger.info("Rotina de inicialização concluída com sucesso")
        return True

    except Exception as e:
        logger.error(f"Falha crítica na inicialização: {str(e)}")
        logger.error(traceback.format_exc())
        return False
    
# --- ENDPOINTS ESSENCIAIS ---
@app.route('/')
def index():
    return render_template("index.html")

@app.route('/api/nfes')
def api_nfes():
    """Endpoint para listar NFes com status"""
    status = request.args.get('status', '').upper()
    
    try:
        with get_mysql_connection() as conn:
            if not conn:
                return jsonify({"error": "Database connection failed"}), 500
            
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT 
                    n.CHAVE_ACESSO_NFEL,
                    n.NUM_NF, 
                    n.NOME_CLIENTE, 
                    n.CIDADE, 
                    n.UF,
                    n.NOME_TRP as transportadora,
                    s.status
                FROM nfe n
                LEFT JOIN nfe_status s ON n.CHAVE_ACESSO_NFEL = s.chave_nfe
                WHERE n.CHAVE_ACESSO_NFEL IS NOT NULL
            """
            
            params = []
            if status:
                query += " AND s.status = %s"
                params.append(status)
            
            query += " ORDER BY s.updated_at DESC LIMIT 100"
            
            cursor.execute(query, params)
            nfes = cursor.fetchall()
            
            return jsonify(nfes)
    
    except Exception as e:
        logger.error(f"Erro em /api/nfes: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/tracking/<chave_nfe>', methods=['GET'])
def api_tracking_details(chave_nfe):
    """Endpoint to retrieve detailed tracking information for a specific NFe"""
    try:
        with get_mysql_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            
            # First, get the base NFe information
            cursor.execute("""
                SELECT 
                    n.NUM_NF as nNF, 
                    n.NOME_CLIENTE as destinatario,
                    n.CIDADE,
                    n.UF
                FROM nfe n
                WHERE n.CHAVE_ACESSO_NFEL = %s
            """, (chave_nfe,))
            nfe_info = cursor.fetchone()
            
            if not nfe_info:
                return jsonify({"error": "Nota fiscal não encontrada"}), 404
            
            # Then, get tracking events
            cursor.execute("""
                SELECT 
                    evento as ocorrencia, 
                    data_hora,
                    status,
                    cidade,
                    uf
                FROM nfe_logs
                WHERE chave_nfe = %s
                ORDER BY data_hora DESC
            """, (chave_nfe,))
            events = cursor.fetchall()
            
            # Combine information
            tracking_data = {
                **nfe_info,
                "items": events
            }
            
            return jsonify(tracking_data)
    
    except mysql.connector.Error as e:
        logger.error(f"Erro em /api/tracking/{chave_nfe}: {str(e)}")
        return jsonify({"error": "Erro ao buscar detalhes de rastreamento"}), 500
    
def parse_tracking_data(tracking_info):
    """Helper function to parse tracking data consistently"""
    if not tracking_info:
        return None
    
    return {
        "nNF": tracking_info.get("nNF", ""),
        "destinatario": tracking_info.get("destinatario", ""),
        "items": tracking_info.get("items", [])
    }

@app.route('/api/status')
def api_status():
    """Endpoint completo de status do sistema"""
    jobs = scheduler.get_jobs()
    
    return jsonify({
        "status": "operacional" if app.inicializado else "inicializando",
        "ultima_importacao": ultima_importacao.isoformat() if ultima_importacao else None,
        "ultima_consulta_api": ultima_consulta_api.isoformat() if ultima_consulta_api else None,
        "proximas_execucoes": {
            "importacao": str(jobs[0].next_run_time) if jobs else None,
            "consulta_api": str(jobs[1].next_run_time) if len(jobs) > 1 else None,
            "atualizacao_estatisticas": str(jobs[2].next_run_time) if len(jobs) > 2 else None
        },
        "metricas": api_metrics
    })

@app.route('/api/categorias')
def api_categorias():
    """Endpoint para consultar status diretamente da nfe_status"""
    try:
        with get_mysql_connection() as conn:
            if not conn:
                return jsonify({"error": "Database connection failed"}), 500
                
            cursor = conn.cursor(dictionary=True)
            
            # Consulta otimizada diretamente na nfe_status
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN status = 'ENTREGUE' THEN 1 END) as entregue,
                    COUNT(CASE WHEN status = 'TRANSITO' THEN 1 END) as transito,
                    COUNT(CASE WHEN status IS NULL OR status = 'NAO_EXPEDIDO' THEN 1 END) as nao_expedido,
                    MAX(updated_at) as ultima_atualizacao
                FROM nfe_status
                WHERE updated_at > DATE_SUB(NOW(), INTERVAL 30 DAY)
            """)
            
            result = cursor.fetchone()
            
            if not result:
                return jsonify({
                    "entregue": 0,
                    "transito": 0,
                    "nao_expedido": 0,
                    "ultima_atualizacao": None
                })
            
            return jsonify({
                "entregue": result['entregue'] or 0,
                "transito": result['transito'] or 0,
                "nao_expedido": result['nao_expedido'] or 0,
                "ultima_atualizacao": result['ultima_atualizacao'].isoformat() if result['ultima_atualizacao'] else None
            })
            
    except Exception as e:
        logger.error(f"Erro em /api/categorias: {str(e)}")
        return jsonify({
            "error": "Erro ao consultar status",
            "details": str(e)
        }), 500

@app.route('/api/transportadoras_filter')
def api_transportadoras():
    """Endpoint para listar transportadoras"""
    try:
        with get_mysql_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT DISTINCT NOME_FAN FROM transportadoras ORDER BY NOME_FAN")
            transportadoras = [row['NOME_FAN'] for row in cursor.fetchall()]
            return jsonify(transportadoras)
    except Exception as e:
        logger.error(f"Erro em /api/transportadoras_filter: {str(e)}")
        return jsonify({"error": "Erro ao buscar transportadoras"}), 500

@app.route('/api/forcar-atualizacao', methods=['POST'])
def forcar_atualizacao():
    """Substitui o antigo /api/arquivos"""
    try:
        logger.info("Forçando atualização manual")
        
        # Executa todas as tarefas imediatamente
        importacao_automatica()
        consulta_api_automatica()
        atualizar_estatisticas_automatico()
        
        return jsonify({
            "status": "sucesso",
            "mensagem": "Todas as tarefas foram executadas"
        })
    except Exception as e:
        return jsonify({
            "status": "erro",
            "mensagem": str(e)
        }), 500

@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    try:
        uptime_seconds = time.time() - app_start_time
        uptime_str = str(timedelta(seconds=uptime_seconds)).split('.')[0]
        
        return jsonify({
            "status": "success",
            "metrics": api_metrics,
            "uptime": {
                "seconds": uptime_seconds,
                "human_readable": uptime_str
            },
            "server_time": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Erro ao coletar métricas: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Erro ao coletar métricas"
        }), 500
        
@app.route('/gerenciamento')
def gerenciamento():
    return render_template("gerenciamento.html")
    
@lru_cache(maxsize=500)
def cached_fetch_tracking_data(chave_nfe):
    """Versão em cache da função de consulta à API"""
    return fetch_tracking_data(chave_nfe)

@app.route('/healthcheck')
def healthcheck():
    services = {
        'oracle': False,
        'mysql': False,
        'api_externa': False
    }
    
    try:
        conn = get_db_connection()
        services['oracle'] = conn is not None
        if conn: conn.close()
    except: pass
    
    try:
        conn = get_mysql_connection()
        services['mysql'] = conn is not None
        if conn: conn.close()
    except: pass
    
    try:
        response = requests.get('https://ssw.inf.br/api', timeout=5)
        services['api_externa'] = response.status_code == 200
    except: pass
    
    return jsonify({
        **services,
        'status': 'OK' if all(services.values()) else 'Degradado',
        'last_import': ultima_importacao.isoformat() if ultima_importacao else None
    })
            
# --- INICIALIZAÇÃO DO SERVIDOR ---
with app.app_context():
    # Inicia a inicialização em uma thread separada para não bloquear
    Thread(target=inicializar_aplicacao, daemon=True).start()

if __name__ == "__main__":
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    logger.info(f"\nServidor pronto em http://{local_ip}:5000")
    logger.info("Endpoints principais:")
    logger.info("- /api/status - Status do sistema")
    logger.info("- /api/categorias - Estatísticas de categorias")
    logger.info("- /api/forcar-atualizacao - Força atualização imediata (POST)")
    
    app.run(host="0.0.0.0", port=5000, debug=False)