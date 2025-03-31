# modules/module_initializer.py
from .database import init_db
from .logger_config import init_logger
from .tracking import init_tracking
from .status import init_status
from .tasks import init_tasks
from .xml_parser import init_xml_parser

def initialize_modules():
    """Inicializa todos os módulos na ordem correta"""
    # 1. Logger primeiro (os outros módulos podem precisar logar)
    init_logger()
    
    # 2. Banco de dados (os outros módulos podem depender dele)
    init_db()
    
    # 3. Demais módulos
    init_tracking()
    init_status()
    init_tasks()
    init_xml_parser()