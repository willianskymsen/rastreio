from flask import Blueprint, render_template, request, jsonify
from modules.database import get_mysql_connection
from modules.logger_config import logger
import mysql.connector

transportadoras_blueprint = Blueprint(
    "transportadoras", __name__, template_folder="templates", static_folder="static"
)


@transportadoras_blueprint.route("/gerenciamento")
def gerenciamento():
    return render_template("gerenciamento.html")


@transportadoras_blueprint.route("transportadoras/api/transportadoras", methods=["GET"])
def get_transportadoras():
    connection = get_mysql_connection()
    if not connection:
        return jsonify({"error": "Erro ao conectar ao banco de dados"}), 500

    try:
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute("""
                SELECT 
                    ID as id,
                    DESCRICAO as descricao,
                    NOME_FAN as nome_fantasia,
                    CNPJ as cnpj,
                    SISTEMA as sistema
                FROM transportadoras
            """)
            transportadoras = cursor.fetchall()

            # Formata o CNPJ para ter sempre 14 dígitos
            for t in transportadoras:
                if t["cnpj"]:
                    t["cnpj"] = str(t["cnpj"]).zfill(14)

            return jsonify(transportadoras), 200

    except mysql.connector.Error as e:
        logger.error(f"Erro ao consultar transportadoras: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if connection.is_connected():
            connection.close()


@transportadoras_blueprint.route("transportadoras/api/atualizar_sistema", methods=["PUT"])
def atualizar_sistema():
    """Atualiza o campo 'SISTEMA' de uma transportadora com o ID da opção."""
    dados = request.json.get("alteracoes", [])

    if not dados:
        return jsonify({"error": "Nenhuma alteração fornecida"}), 400

    connection = get_mysql_connection()
    if not connection:
        return jsonify({"error": "Erro ao conectar ao banco"}), 500

    try:
        with connection.cursor() as cursor:
            for alteracao in dados:
                id_transportadora = alteracao.get("id")
                id_opcao_sistema = alteracao.get("sistema")  # Agora esperamos o ID da opção

                if not isinstance(id_transportadora, int) or not id_opcao_sistema:
                    return jsonify(
                        {"error": "ID inválido ou sistema não informado"}
                    ), 400

                # Verifica se a opção existe
                cursor.execute("SELECT id FROM opcoes_sistema WHERE id = %s", (id_opcao_sistema,))
                if not cursor.fetchone():
                    return jsonify({"error": "Opção de sistema não encontrada"}), 404

                # Atualiza com o ID da opção
                cursor.execute(
                    """
                    UPDATE transportadoras 
                    SET SISTEMA = %s 
                    WHERE ID = %s
                    """,
                    (id_opcao_sistema, id_transportadora),
                )

            connection.commit()

        return jsonify(
            {"success": True, "message": "Sistema(s) atualizado(s) com sucesso"}
        ), 200

    except mysql.connector.Error as e:
        connection.rollback()
        logger.error(f"Erro ao atualizar sistema: {e}")
        return jsonify(
            {"error": "Erro ao atualizar banco de dados", "details": str(e)}
        ), 500
    finally:
        if connection.is_connected():
            connection.close()


@transportadoras_blueprint.route("/gerenciar_opcoes", methods=["GET"])
def gerenciar_opcoes():
    """Endpoint para servir a página HTML de gerenciamento de opções"""
    try:
        return render_template("opcoes.html")
    except Exception as e:
        logger.error(f"Erro ao carregar página de opções: {e}")
        return jsonify({"error": "Erro ao carregar página"}), 500


@transportadoras_blueprint.route("transportadoras/api/opcoes_sistema/listar", methods=["GET"])
def get_opcoes_sistema():
    try:
        connection = get_mysql_connection()
        cursor = connection.cursor(dictionary=True)
        
        cursor.execute("SELECT id, tipo, valor, ativo FROM opcoes_sistema ORDER BY valor")
        opcoes = cursor.fetchall()
        
        # DEBUG: Log dos dados retornados do banco
        print("Dados retornados do banco:", opcoes)
        
        return jsonify({
            "success": True,
            "data": opcoes,
            "count": len(opcoes)
        })
        
    except Exception as e:
        logger.error(f"Erro ao consultar opções: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if connection.is_connected():
            connection.close()


@transportadoras_blueprint.route("transportadoras/api/opcoes_sistema/criar", methods=["POST"])
def create_opcao_sistema():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Dados JSON inválidos"}), 400

        # Validação dos campos obrigatórios
        if "tipo" not in data or "valor" not in data:
            return jsonify({"error": "Tipo e valor são obrigatórios"}), 400

        # Validação dos tamanhos máximos
        if len(data.get("tipo", "")) > 50:
            return jsonify({"error": "O campo 'tipo' deve ter no máximo 50 caracteres"}), 400
            
        if len(data.get("valor", "")) > 255:
            return jsonify({"error": "O campo 'valor' deve ter no máximo 255 caracteres"}), 400

        # Define o valor padrão para 'ativo' se não fornecido
        data["ativo"] = 1 if data.get("ativo", True) else 0

        connection = get_mysql_connection()
        if not connection:
            return jsonify({"error": "Erro ao conectar ao banco"}), 500

        cursor = connection.cursor()
        try:
            cursor.execute(
                """
                INSERT INTO opcoes_sistema (tipo, valor, ativo)
                VALUES (%s, %s, %s)
            """,
                (data["tipo"].upper(), data["valor"], data["ativo"]),
            )

            connection.commit()
            new_id = cursor.lastrowid

            return jsonify({
                "success": True, 
                "id": new_id,
                "message": "Opção criada com sucesso"
            }), 201

        except mysql.connector.Error as db_error:
            connection.rollback()
            logger.error(f"Erro MySQL: {db_error}")
            return jsonify({
                "error": "Erro interno no banco de dados",
                "details": str(db_error)
            }), 500

        finally:
            if cursor:
                cursor.close()
            if connection.is_connected():
                connection.close()

    except Exception as e:
        logger.error(f"Erro geral: {str(e)}")
        return jsonify({
            "error": "Erro interno no servidor",
            "details": str(e)
        }), 500


@transportadoras_blueprint.route("transportadoras/api/opcoes_sistema/<int:id>", methods=["PUT"])
def update_opcao_sistema(id):
    """Atualiza uma opção existente com validações"""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Dados JSON inválidos"}), 400

        # Validações
        if 'tipo' not in data or 'valor' not in data:
            return jsonify({"error": "Tipo e valor são obrigatórios"}), 400

        if len(data['tipo']) > 50:
            return jsonify({"error": "Tipo deve ter no máximo 50 caracteres"}), 400

        if len(data['valor']) > 255:
            return jsonify({"error": "Valor deve ter no máximo 255 caracteres"}), 400

        connection = get_mysql_connection()
        if not connection:
            return jsonify({"error": "Erro ao conectar ao banco"}), 500

        with connection.cursor() as cursor:
            # Verifica se existe
            cursor.execute("SELECT id FROM opcoes_sistema WHERE id = %s", (id,))
            if not cursor.fetchone():
                return jsonify({"error": "Opção não encontrada"}), 404

            # Atualização
            cursor.execute("""
                UPDATE opcoes_sistema 
                SET tipo = %s, 
                    valor = %s, 
                    ativo = %s, 
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (
                data['tipo'].upper(),
                data['valor'],
                data.get('ativo', 1),
                id
            ))
            
            connection.commit()

        return jsonify({
            "success": True,
            "message": "Opção atualizada com sucesso"
        })

    except Exception as e:
        connection.rollback()
        logger.error(f"Erro ao atualizar opção {id}: {str(e)}")
        return jsonify({
            "error": "Erro ao atualizar opção",
            "details": str(e)
        }), 500
    finally:
        if connection.is_connected():
            connection.close()


@transportadoras_blueprint.route("transportadoras/api/opcoes_sistema/<int:id>", methods=["DELETE"])
def delete_opcao_sistema(id):
    """Remove uma opção do sistema com verificações"""
    try:
        connection = get_mysql_connection()
        if not connection:
            return jsonify({"error": "Erro ao conectar ao banco"}), 500

        with connection.cursor() as cursor:
            # Verifica existência
            cursor.execute("SELECT id FROM opcoes_sistema WHERE id = %s", (id,))
            if not cursor.fetchone():
                return jsonify({"error": "Opção não encontrada"}), 404

            # Verifica se está em uso (exemplo)
            cursor.execute("SELECT 1 FROM transportadoras WHERE sistema = (SELECT valor FROM opcoes_sistema WHERE id = %s) LIMIT 1", (id,))
            if cursor.fetchone():
                return jsonify({
                    "error": "Esta opção está em uso por transportadoras",
                    "code": "in_use"
                }), 400

            # Exclusão
            cursor.execute("DELETE FROM opcoes_sistema WHERE id = %s", (id,))
            connection.commit()

        return jsonify({
            "success": True,
            "message": "Opção excluída com sucesso"
        })

    except Exception as e:
        connection.rollback()
        logger.error(f"Erro ao excluir opção {id}: {str(e)}")
        return jsonify({
            "error": "Erro ao excluir opção",
            "details": str(e)
        }), 500
    finally:
        if connection.is_connected():
            connection.close()
