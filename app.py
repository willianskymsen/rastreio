from flask import Flask, send_from_directory
from waitress import serve
from modules.module_initializer import initialize_modules
from rastro.rastro import rastro_blueprint
from transportadoras.transportadoras import transportadoras_blueprint
from acesso.acesso import acesso_blueprint
from status.status import status_blueprint
from modules.tasks import init_tasks, start_background_process
import logging
import os
from dotenv import load_dotenv

# Configuração inicial otimizada
load_dotenv()  # Carrega as variáveis do arquivo .env

# Configuração de logging mais robusta
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# Criação do app Flask com configurações otimizadas
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get('SECRET_KEY', 'fallback_key_altere_isto'),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SECURE=False,  # Mude para True se usar HTTPS
    PERMANENT_SESSION_LIFETIME=86400,  # 1 dia em segundos
    TEMPLATES_AUTO_RELOAD=False  # Desligar em produção
)

# Registrar blueprints com URLs prefixadas
app.register_blueprint(rastro_blueprint, url_prefix='/rastro')
app.register_blueprint(transportadoras_blueprint, url_prefix='/transportadoras')
app.register_blueprint(status_blueprint, url_prefix='/status')
app.register_blueprint(acesso_blueprint, url_prefix='/acesso')

# Rota para favicon otimizada
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, 'static'),
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )

# Configuração do Waitress otimizada
def configure_waitress():
    # Configurações baseadas no número de CPUs
    num_threads = int(os.environ.get('WAITRESS_THREADS', 4))  # Default 4 threads
    max_request_body_size = int(os.environ.get('MAX_BODY_SIZE', 1073741824))  # 1GB
    
    return {
        'host': '127.0.0.1',  # Mais performático que '0.0.0.0'
        'port': 5000,
        'threads': num_threads,
        'channel_timeout': 60,
        'connection_limit': 1000,
        'asyncore_loop_timeout': 1,
        'send_bytes': 4096,
        'outbuf_high_watermark': 16777216,  # 16MB
        #'inbuf_high_watermark': 16777216,   # 16MB
        'max_request_body_size': max_request_body_size,
        'clear_untrusted_proxy_headers': True
    }

def start_server():
    """Inicializa o servidor com todas as dependências"""
    logger.info("Iniciando inicialização dos módulos...")
    initialize_modules()
    
    logger.info("Inicializando tasks...")
    init_tasks()
    start_background_process()
    
    # Mostrar rotas disponíveis apenas em desenvolvimento
    if os.environ.get('FLASK_ENV') == 'development':
        print(app.url_map)
    
    # Configura e inicia o Waitress
    waitress_config = configure_waitress()
    logger.info(f"Iniciando Waitress com configuração: {waitress_config}")
    
    serve(app, **waitress_config)

if __name__ == "__main__":
    start_server()