import time
from config import MYSQL_CONFIG
import mysql.connector
from mysql.connector import errorcode

def test_mysql_connection():
    """Teste de conexão com schema corrigido"""
    print("\n=== TESTE DE CONEXÃO MARIA DB ===\n")
    
    conn = None
    cursor = None
    
    try:
        # 1. Conexão básica
        print("1. Conectando ao banco...")
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        
        if not conn.is_connected():
            print("❌ Conexão inativa")
            return False
            
        print(f"✅ Conectado ao MariaDB {conn.get_server_info()}")
        print(f"ID da conexão: {conn.connection_id}")

        # 2. Consulta de versão
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT VERSION() AS version")
        version = cursor.fetchone()['version']
        print(f"\n2. Versão do servidor: {version}")

        # 3. Verificação de tabelas e estrutura
        cursor.execute("DESCRIBE opcoes_sistema")
        opcoes_sistema_fields = [row['Field'] for row in cursor]
        print("\n3. Campos da tabela transportadoras:", ", ".join(opcoes_sistema_fields))

        # 4. Teste transacional corrigido
        print("\n4. Teste transacional...")
        try:
            # Verifica/limpa transações pendentes
            if conn.in_transaction:
                conn.rollback()
                print("⚠️ Transação pendente foi rollbackada")
            
            # Prepara dados com todos campos obrigatórios
            test_data = (
                f"TEST_{int(time.time())}",
                "TESTE_CONEXAO",
                time.strftime('%Y-%m-%d %H:%M:%S'),
                'TESTE',  # status
                'TESTE',  # transportadora
                'TESTE',  # cidade
                'TE'      # uf
            )
            
            # Query dinâmica baseada nos campos existentes
            fields = ['chave_nfe', 'evento', 'data_hora', 'status', 
                     'transportadora', 'cidade', 'uf']
            placeholders = ", ".join(["%s"] * len(fields))
            
            cursor.execute(f"""
                INSERT INTO nfe_logs 
                ({", ".join(fields)}) 
                VALUES ({placeholders})
            """, test_data)
            
            conn.rollback()
            print("✅ Teste transacional completo (rollback realizado)")
            
        except Exception as e:
            print(f"❌ Erro na transação: {str(e)}")
            if conn.is_connected():
                conn.rollback()

    except mysql.connector.Error as err:
        print(f"\n❌ Erro MySQL (code {err.errno}): {err.msg}")
        return False
        
    except Exception as e:
        print(f"\n❌ Erro inesperado: {str(e)}")
        return False
        
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
            print("\n✅ Conexão encerrada corretamente")

    print("\n=== TESTE CONCLUÍDO ===")
    return True

if __name__ == "__main__":
    test_mysql_connection()