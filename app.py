from flask import Flask, jsonify, render_template, request
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import os

app = Flask(__name__)

# Pasta onde os arquivos XML estão armazenados
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Diretório do script atual
XML_FOLDER = os.path.join(BASE_DIR, "xml")  # Caminho completo para a pasta 'xml'

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
        if chNFe is None:
            print("Tag <chNFe> não encontrada no XML.")
            return None
        
        return chNFe.text  # Retorna o texto da chave
    except Exception as e:
        print(f"Erro ao processar o arquivo XML: {e}")
        return None

def fetch_tracking_data(chave_nfe):
    """Faz a requisição à API e retorna os dados processados com base na chave da NF-e."""
    url = "https://ssw.inf.br/api/trackingdanfe"
    data = {'chave_nfe': chave_nfe}  # Formato correto
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    
    try:
        response = requests.post(url, data=data, headers=headers, timeout=10)
        response.raise_for_status()  # Levanta uma exceção para códigos de status HTTP 4xx/5xx
        return parse_xml(response.text)
    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição à API: {e}")
        return None

def parse_xml(xml_data):
    """Processa o XML de rastreamento e retorna os dados formatados."""
    try:
        # Faz o parse do XML
        root = ET.fromstring(xml_data)
        
        # Verifica se o documento foi encontrado
        success = root.find(".//success")
        if success is None or success.text.lower() != "true":
            print("Documento não localizado ou sucesso falso.")
            return None
        
        # Extrai o destinatário e o número da NF-e
        header = root.find(".//header")
        if header is None:
            print("Tag <header> não encontrada no XML.")
            return None
        
        destinatario = header.find("destinatario")
        nro_nf = header.find("nro_nf")
        
        if destinatario is None or nro_nf is None:
            print("Tags <destinatario> ou <nro_nf> não encontradas no XML.")
            return None
        
        # Extrai os eventos de rastreamento
        items = []
        for item in root.findall(".//item"):
            data_hora = item.find("data_hora")
            ocorrencia = item.find("ocorrencia")
            descricao = item.find("descricao")
            tipo = item.find("tipo")
            nome_recebedor = item.find("nome_recebedor")
            
            if None in [data_hora, ocorrencia, descricao, tipo]:
                continue  # Ignora itens incompletos
            
            # Mantém a data no formato ISO 8601 para ordenação
            items.append({
                "data_hora": data_hora.text,  # Mantém como string ISO 8601
                "ocorrencia": ocorrencia.text,
                "descricao": descricao.text,
                "tipo": tipo.text,
                "nome_recebedor": nome_recebedor.text if nome_recebedor is not None else ""
            })
        
        return {"destinatario": destinatario.text, "nNF": nro_nf.text, "items": items}
    except Exception as e:
        print(f"Erro ao processar o XML da API: {e}")
        return None

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/api/arquivos', methods=['GET'])
def api_arquivos():
    """Retorna a lista de arquivos XML na pasta com o número da NF-e."""
    if not os.path.exists(XML_FOLDER):
        return jsonify({"error": f"Pasta 'xml' não encontrada em {XML_FOLDER}"}), 404
    
    xml_files = [f for f in os.listdir(XML_FOLDER) if f.endswith('.xml')]
    if not xml_files:
        return jsonify({"error": "Nenhum arquivo XML encontrado na pasta 'xml/'"}), 404
    
    arquivos_info = []
    for file in xml_files:
        xml_file_path = os.path.join(XML_FOLDER, file)
        try:
            tree = ET.parse(xml_file_path)
            root = tree.getroot()
            
            # Extrai o número da NF-e
            nNF = root.find(".//nfe:ide/nfe:nNF", namespaces={'nfe': 'http://www.portalfiscal.inf.br/nfe'})
            if nNF is None:
                print(f"Tag <nNF> não encontrada no arquivo {file}.")
                continue
            
            arquivos_info.append({"filename": file, "nNF": nNF.text})
        except Exception as e:
            print(f"Erro ao processar o arquivo {file}: {e}")
            continue
    
    return jsonify(arquivos_info)

@app.route('/api/dados', methods=['POST'])
def api_dados():
    # Obtém o nome do arquivo enviado pelo frontend
    filename = request.json.get("filename")
    if not filename:
        return jsonify({"error": "Nome do arquivo não fornecido"}), 400
    
    # Caminho completo do arquivo
    xml_file_path = os.path.join(XML_FOLDER, filename)
    if not os.path.exists(xml_file_path):
        return jsonify({"error": f"Arquivo '{filename}' não encontrado na pasta 'xml/'"}), 404
    
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
        try:
            os.makedirs(XML_FOLDER)
            print(f"Pasta '{XML_FOLDER}' criada com sucesso.")
        except Exception as e:
            print(f"Erro ao criar a pasta '{XML_FOLDER}': {e}")
            exit(1)
    
    app.run(debug=True)