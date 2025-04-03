# modules/module_initializer.py
import logging
from .database import init_databases
from .tasks import init_tasks
from .json_parser import init_json_parser
from .status import init_status
from .nfe_tracking_logger import init_logger  # Garanta que esta linha esteja presente
from .nfe_status_sync import sync_nfe_to_nfe_status_periodically

logger = logging.getLogger(__name__)

def initialize_modules():
    """Initializes all the modules of the application."""
    logger.info("Initializing modules...")

    init_databases()
    logger.info("Database module initialized.")

    init_tasks()
    logger.info("Tasks module initialized.")

    init_json_parser()
    logger.info("JSON Parser module initialized.")

    init_status()
    logger.info("Status module initialized.")

    init_logger()  # Chama a função init_logger do nfe_tracking_logger
    logger.info("Logger module initialized.")

    # Inicia a sincronização periódica em uma thread separada
    import threading
    sync_thread = threading.Thread(target=sync_nfe_to_nfe_status_periodically, daemon=True)
    sync_thread.start()
    logger.info("NFe status synchronization started in a background thread.")

    logger.info("All modules initialized successfully.")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    initialize_modules()