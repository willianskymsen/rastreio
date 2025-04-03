# help/help_manager.py
from .database import help_database_module  # Importe a função de ajuda específica

def show_help(module):
    """Exibe a ajuda para o módulo especificado."""
    import inspect
    print("=" * 40)
    print(f"Ajuda para o módulo: {module.__name__}")
    print("=" * 40)
    print(inspect.getdoc(module) or "Nenhuma documentação disponível.")
    print("\n")

    print("-" * 40)
    print("Funções:")
    print("-" * 40)
    for name, obj in inspect.getmembers(module):
        if inspect.isfunction(obj):
            print(f"\nFunção: {name}")
            docstring = inspect.getdoc(obj)
            if docstring:
                print(docstring)
            else:
                print("Nenhuma documentação disponível.")
    print("=" * 40)

def show_database_help():
    """Exibe a ajuda para o módulo database."""
    # A função de ajuda já está implementada no database.py
    # Podemos simplesmente chamá-la aqui se quisermos essa abordagem.
    help_database_module()

# ... outras funções de ajuda para outros módulos ...

if __name__ == "__main__":
    # Exemplo de como usar
    show_database_help()
    print("\n" + "=" * 40 + "\n")
    # Você poderia adicionar chamadas para outras funções de ajuda aqui
    # Ex: show_config_help() se você tivesse uma função para o módulo config