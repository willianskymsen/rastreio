from flask import Flask, send_from_directory
from modules.module_initializer import initialize_modules
from rastro.rastro import rastro_blueprint
from transportadoras.transportadoras import transportadoras_blueprint
from rastreio.rastreio import rastreio_blueprint
from status.status import status_blueprint
from modules.tasks import init_tasks, start_background_process
from flask_moment import Moment
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Registrar blueprint
app.register_blueprint(rastro_blueprint, url_prefix='/rastro')
app.register_blueprint(transportadoras_blueprint, url_prefix='/transportadoras')
app.register_blueprint(status_blueprint, url_prefix='/status')
app.register_blueprint(rastreio_blueprint, url_prefix='/')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico', mimetype='image/vnd.microsoft.icon')

# Mostrar rotas disponíveis
print(app.url_map)

if __name__ == "__main__":
    # Inicializa todos os módulos antes de rodar o app
    initialize_modules()
    logger.info("Módulos inicializados.")

    # Inicializar as tasks
    init_tasks()

    # Iniciar o processo de agendamento em background
    start_background_process()

    app.run(host="0.0.0.0", port=5000, debug=True)