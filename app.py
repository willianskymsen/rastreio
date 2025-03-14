from flask import Flask, jsonify, render_template, request
import requests
import pandas as pd
import xml.etree.ElementTree as ET
from datetime import datetime
import os

app = Flask(__name__)

# Pasta onde os arquivos XML estão armazenados
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # Diretório do script atual
XML_FOLDER = os.path.join(BASE_DIR, "xml")  # Caminho completo para a pasta 'xml'

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
    try:
        # Carrega a planilha Excel
        df = pd.read_excel(os.path.join(BASE_DIR, "notas.xlsx"))
        
        # Verifica se as colunas necessárias existem
        if 'NUM_NF' not in df.columns or 'CHAVE' not in df.columns:
            return jsonify({"error": "Planilha não contém as colunas 'NUM_NF' e 'CHAVE'"}), 400
        
        # Cria a lista de arquivos (agora baseada na planilha)
        arquivos_info = []
        for index, row in df.iterrows():
            arquivos_info.append({
                "filename": str(row['NUM_NF']),  # Usamos NUM_NF como identificador
                "nNF": row['NUM_NF']            # Número da NF-e
            })
        
        return jsonify(arquivos_info)
    except Exception as e:
        print(f"Erro ao ler a planilha Excel: {e}")
        return jsonify({"error": "Erro ao processar a planilha de notas"}), 500

@app.route('/api/dados', methods=['POST'])
def api_dados():
    try:
        # Obtém o número da NF-e enviado pelo frontend
        num_nf = request.json.get("filename")
        if not num_nf:
            return jsonify({"error": "Número da NF-e não fornecido"}), 400
        
        # Carrega a planilha Excel
        df = pd.read_excel(os.path.join(BASE_DIR, "notas.xlsx"))
        
        # Filtra a linha correspondente ao número da NF-e
        nf_info = df[df['NUM_NF'] == int(num_nf)]
        if nf_info.empty:
            return jsonify({"error": f"NF-e {num_nf} não encontrada na planilha"}), 404
        
        # Obtém a chave da NF-e da coluna 'CHAVE'
        chave_nfe = nf_info['CHAVE'].values[0]
        
        # Busca os dados de rastreamento
        dados = fetch_tracking_data(chave_nfe)
        if dados:
            return jsonify(dados)
        else:
            return jsonify({"error": "Não foi possível obter os dados de rastreamento"}), 500
    except Exception as e:
        print(f"Erro ao processar a requisição: {e}")
        return jsonify({"error": "Erro interno no servidor"}), 500

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