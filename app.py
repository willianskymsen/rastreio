from flask import Flask, jsonify, send_from_directory, request  # Adicionei o request aqui
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import os

app = Flask(__name__)

# Pasta onde os arquivos XML estão armazenados
XML_FOLDER = "xml"

def extract_key_from_xml(xml_file):
    """Extrai a chave da NF-e de um arquivo XML."""
    try:
        # Define o namespace do XML
        namespaces = {
            'nfe': 'http://www.portalfiscal.inf.br/nfe'
        }
        
        # Faz o parse do arquivo XML
        tree = ET.parse(xml_file)
        root = tree.getroot()
        
        # Encontra a tag <chNFe> dentro de <infProt>
        chNFe = root.find(".//nfe:infProt/nfe:chNFe", namespaces)
        
        if chNFe is not None:
            return chNFe.text  # Retorna o texto da chave
        else:
            print("Chave NF-e não encontrada no XML.")
            return None
    except Exception as e:
        print(f"Erro ao processar o arquivo XML: {e}")
        return None

def fetch_tracking_data(chave_nfe):
    """Faz a requisição à API e retorna os dados processados com base na chave da NF-e."""
    url = "https://ssw.inf.br/api/trackingdanfe"
    data = {'chave_nfe': chave_nfe}  # Formato correto
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    
    response = requests.post(url, data=data, headers=headers)  # Envia os dados no formato correto
    
    if response.status_code == 200:
        return parse_xml(response.text)
    else:
        print(f"Erro {response.status_code}: {response.text}")  # Log para depuração
        return None

def parse_xml(xml_data):
    """Processa o XML e retorna os dados formatados."""
    root = ET.fromstring(xml_data)
    
    destinatario = root.find(".//destinatario").text
    nro_nf = root.find(".//nro_nf").text
    
    items = []
    for item in root.findall(".//item"):
        data_hora = item.find("data_hora").text
        data_formatada = datetime.strptime(data_hora, "%Y-%m-%dT%H:%M:%S").strftime("%d/%m/%Y %H:%M")
        
        items.append({
            "data_hora": data_formatada,
            "ocorrencia": item.find("ocorrencia").text,
            "descricao": item.find("descricao").text,
            "tipo": item.find("tipo").text,
            "nome_recebedor": item.find("nome_recebedor").text if item.find("nome_recebedor") is not None else ""
        })
    
    return {"destinatario": destinatario, "nro_nf": nro_nf, "items": items}

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/api/arquivos', methods=['GET'])
def api_arquivos():
    """Retorna a lista de arquivos XML na pasta."""
    xml_files = [f for f in os.listdir(XML_FOLDER) if f.endswith('.xml')]
    return jsonify(xml_files)

@app.route('/api/dados', methods=['POST'])
def api_dados():
    # Obtém o nome do arquivo enviado pelo frontend
    filename = request.json.get("filename")
    if not filename:
        return jsonify({"error": "Nome do arquivo não fornecido"}), 400
    
    # Caminho completo do arquivo
    xml_file_path = os.path.join(XML_FOLDER, filename)
    
    # Extrai a chave da NF-e do XML
    chave_nfe = extract_key_from_xml(xml_file_path)
    if not chave_nfe:
        return jsonify({"error": "Não foi possível extrair a chave da NF-e do XML"}), 400
    
    # Busca os dados de rastreamento
    dados = fetch_tracking_data(chave_nfe)
    if dados:
        return jsonify(dados)
    else:
        return jsonify({"error": "Não foi possível obter os dados"}), 500

if __name__ == "__main__":
    # Cria a pasta 'xml' se ela não existir
    if not os.path.exists(XML_FOLDER):
        os.makedirs(XML_FOLDER)
    
    app.run(debug=True)