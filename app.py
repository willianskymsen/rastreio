from flask import Flask
from rastro.rastro import rastro_blueprint
from modules.module_initializer import initialize_modules

app = Flask(__name__)

# Registrar blueprint
app.register_blueprint(rastro_blueprint, url_prefix='/rastro')

# Mostrar rotas disponíveis
print(app.url_map)

if __name__ == "__main__":
    # Inicializa todos os módulos antes de rodar o app
    initialize_modules()
    app.run(host="0.0.0.0", port=5000, debug=True)