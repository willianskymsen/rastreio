from flask import Flask, send_from_directory
from rastro.rastro import rastro_blueprint
from modules.module_initializer import initialize_modules
from transportadoras.transportadoras import transportadoras_blueprint

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
    app.run(host="0.0.0.0", port=5000, debug=True)