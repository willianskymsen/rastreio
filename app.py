from flask import Flask, send_from_directory
from rastro.rastro import rastro_blueprint
from modules.module_initializer import initialize_modules
from transportadoras.transportadoras import transportadoras_blueprint
from modules.tasks import check_and_process_nfes, run_scheduled_tasks # Importe as funções necessárias
import threading
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Registrar blueprint
app.register_blueprint(rastro_blueprint, url_prefix='/rastro')
app.register_blueprint(transportadoras_blueprint, url_prefix='/transportadoras')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory('static', 'favicon.ico', mimetype='image/vnd.microsoft.icon')

# Mostrar rotas disponíveis
print(app.url_map)

if __name__ == "__main__":
    # Inicializa todos os módulos antes de rodar o app
    initialize_modules()
    logger.info("Módulos inicializados.")

    # Execute a verificação inicial de NF-es pendentes
    logger.info("Executando verificação inicial de NF-es pendentes...")
    check_and_process_nfes()
    logger.info("Verificação inicial de NF-es pendentes concluída.")

    # Inicie a rotina de tarefas agendadas em um thread separado
    def run_tasks_in_background():
        run_scheduled_tasks()

    task_thread = threading.Thread(target=run_tasks_in_background, daemon=True)
    task_thread.start()
    logger.info("Rotina de tarefas agendadas iniciada em background.")

    app.run(host="0.0.0.0", port=5000, debug=True)