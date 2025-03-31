document.addEventListener('DOMContentLoaded', function() {
    // Elementos DOM
    const form = document.getElementById('formOpcaoSistema');
    const tabelaOpcoes = document.getElementById('tabelaOpcoes');

    // Carrega opções ao iniciar
    carregarOpcoes();

    // Evento de submit do formulário
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        salvarOpcao();
    });

    // Evento do botão limpar
    document.getElementById('btnLimpar').addEventListener('click', limparFormulario);
});

async function carregarOpcoes() {
    try {
        const response = await fetch('/api/opcoes_sistema/listar');
        const data = await response.json();

        console.log("Resposta da API ao buscar opções:", data);

        if (!response.ok) {
            throw new Error(data.error || `Erro HTTP: ${response.status}`);
        }

        // Verifica se data é um array antes de renderizar
        if (Array.isArray(data)) {
            renderizarOpcoes(data);
        } else {
            throw new Error("A resposta da API não é um array.");
        }
    } catch (error) {
        console.error('Erro ao carregar opções:', error);
        mostrarErro('Erro ao carregar opções: ' + error.message);
    }
}

async function salvarOpcao() {
    const opcao = {
        tipo: document.getElementById('tipo').value,
        valor: document.getElementById('valor').value,
        ativo: document.getElementById('ativo').checked ? 1 : 0 // Converte para 1 ou 0
    };

    console.log("Enviando dados:", opcao);

    try {
        const response = await fetch('/api/opcoes_sistema/criar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(opcao)
        });

        const data = await response.json();
        console.log("Resposta completa:", response, data);

        if (!response.ok) {
            throw new Error(data.error || data.details || `Erro ${response.status}`);
        }

        await carregarOpcoes();
        limparFormulario();
        mostrarSucesso(`Opção criada com ID: ${data.id}`);
    } catch (error) {
        console.error("Erro completo:", error);
        mostrarErro(`Falha ao criar: ${error.message}`);
    }
}

async function editarOpcao(id) {
    try {
        const response = await fetch(`/api/opcoes-sistema/${id}`);
        const opcao = await response.json();

        document.getElementById('opcaoId').value = opcao.id;
        document.getElementById('tipo').value = opcao.tipo;
        document.getElementById('valor').value = opcao.valor;
        document.getElementById('ativo').checked = opcao.ativo;

        window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (error) {
        console.error('Erro ao editar opção:', error);
        alert('Erro ao carregar opção para edição.');
    }
}

async function excluirOpcao(id) {
    if (!confirm('Tem certeza que deseja excluir esta opção?')) return;

    try {
        const response = await fetch(`/api/opcoes-sistema/${id}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error(`Erro HTTP: ${response.status}`);
        }

        await carregarOpcoes();
        alert('Opção excluída com sucesso!');
    } catch (error) {
        console.error('Erro ao excluir opção:', error);
        alert('Erro ao excluir opção. Verifique o console.');
    }
}

function renderizarOpcoes(opcoes) {
    const tabelaOpcoes = document.getElementById('tabelaOpcoes');
    
    // Limpa o conteúdo anterior da tabela
    tabelaOpcoes.innerHTML = '';

    // Verifica se há opções para exibir
    if (!Array.isArray(opcoes) || opcoes.length === 0) {
        tabelaOpcoes.innerHTML = '<tr><td colspan="5">Nenhuma opção cadastrada.</td></tr>';
        return;
    }

    // Ordena as opções pelo ID (crescente)
    opcoes.sort((a, b) => a.id - b.id); // Ordena de forma crescente (de menor para maior)

    // Percorre os dados e cria as linhas da tabela
    opcoes.forEach(opcao => {
        const linha = document.createElement('tr');

        linha.innerHTML = `
            <td>${opcao.id}</td>
            <td>${opcao.tipo}</td>
            <td>${opcao.valor}</td>
            <td>${opcao.ativo ? 'Sim' : 'Não'}</td>
            <td>
                <button onclick="editarOpcao(${opcao.id})">Editar</button>
                <button onclick="excluirOpcao(${opcao.id})">Excluir</button>
            </td>
        `;

        tabelaOpcoes.appendChild(linha);
    });
}

function limparFormulario() {
    document.getElementById('formOpcaoSistema').reset();
    document.getElementById('opcaoId').value = '';
}

function mostrarErro(mensagem) {
    alert('Erro: ' + mensagem); // Pode substituir por um toast ou modal mais elegante
}

function mostrarSucesso(mensagem) {
    alert(mensagem); // Pode substituir por um toast ou modal mais elegante
}
