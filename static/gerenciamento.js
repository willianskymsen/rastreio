document.addEventListener("DOMContentLoaded", function () {
    carregarTransportadoras();
    carregarOpcoesSistema();

    const selecionarTodosCheckbox = document.getElementById('selecionar-todos');
    if (selecionarTodosCheckbox) {
        selecionarTodosCheckbox.addEventListener('change', (event) => {
            document.querySelectorAll('.selecionar-linha').forEach(checkbox => {
                checkbox.checked = event.target.checked;
            });
        });
    }

    const salvarAlteracoesButton = document.getElementById('salvar-alteracoes');
    if (salvarAlteracoesButton) {
        salvarAlteracoesButton.addEventListener('click', async () => {
            const novaOpcao = document.getElementById('alteracao-em-massa').value;
            if (!novaOpcao) {
                exibirMensagem('Por favor, selecione uma opção para alteração.', 'erro');
                return;
            }

            const alteracoes = Array.from(document.querySelectorAll('.selecionar-linha:checked')).map(checkbox => {
                return { id: parseInt(checkbox.getAttribute('data-id'), 10), sistema: novaOpcao };
            });

            if (alteracoes.length === 0) {
                exibirMensagem('Por favor, selecione pelo menos uma transportadora.', 'erro');
                return;
            }

            console.log('Dados a serem enviados:', alteracoes);
            
            try {
                const response = await fetch('/api/atualizar_sistema', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ alteracoes })
                });

                const data = await response.json();
                if (!data.success) throw new Error(data.error || 'Erro desconhecido');

                exibirMensagem('Alterações realizadas com sucesso!', 'sucesso', true);
            } catch (error) {
                console.error('Erro ao realizar alteração em massa:', error);
                exibirMensagem('Erro ao salvar alterações.', 'erro');
            }
        });
    }
    // Adiciona evento de clique nos cabeçalhos da tabela para ordenar
    document.querySelectorAll("th.clickable").forEach((header, index) => {
        header.addEventListener("click", () => ordenarTabela(index));
    });
});

let transportadoras = []; // Armazena os dados para ordenação
let ordenacao = {}; // Armazena estado da ordenação para cada coluna

async function carregarTransportadoras() {
    try {
        document.getElementById('loading').style.display = 'block';
        document.getElementById('mensagem').style.display = 'none';

        const response = await fetch('/api/transportadoras');
        if (!response.ok) throw new Error(`Erro HTTP: ${response.status}`);

        transportadoras = await response.json();
        if (!Array.isArray(transportadoras)) throw new Error('Formato de dados inválido');

        renderizarTabela(transportadoras);
    } catch (error) {
        console.error('Erro ao carregar transportadoras:', error);
        document.getElementById('mensagem').textContent = `Erro: ${error.message}`;
        document.getElementById('mensagem').style.display = 'block';
    } finally {
        document.getElementById('loading').style.display = 'none';
    }
}

async function carregarOpcoesSistema() {
    try {
        const response = await fetch('/api/opcoes_sistema/listar');
        if (!response.ok) throw new Error(`Erro HTTP: ${response.status}`);

        const opcoes = await response.json();
        if (!Array.isArray(opcoes)) throw new Error('Formato inválido');

        const selectAlteracaoEmMassa = document.getElementById('alteracao-em-massa');
        selectAlteracaoEmMassa.innerHTML = '<option value="">Selecione</option>';

        opcoes.forEach(opcao => {
            const option = document.createElement('option');
            option.value = opcao.tipo;
            option.textContent = opcao.tipo;
            selectAlteracaoEmMassa.appendChild(option);
        });
    } catch (error) {
        console.error('Erro ao carregar opções do sistema:', error);
    }
}

function renderizarTabela(dados) {
    const tabelaCorpo = document.getElementById('tabela-corpo');
    tabelaCorpo.innerHTML = '';

    if (dados.length === 0) {
        tabelaCorpo.innerHTML = `<tr><td colspan="8" class="no-data">Nenhuma transportadora cadastrada</td></tr>`;
        return;
    }

    dados.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td><input type="checkbox" class="selecionar-linha" data-id="${item.ID}"></td>
            <td>${item.ID ?? '-'}</td>
            <td>${item.COD_FOR ?? '-'}</td>
            <td>${item.DESCRICAO ?? '-'}</td>
            <td>${item.NOME_FAN ?? '-'}</td>
            <td>${formatarCNPJ(item.CNPJ)}</td>
            <td>${item.INSC_EST ?? '-'}</td>
            <td>${item.INSC_MUN ?? '-'}</td>
            <td>${item.SISTEMA ?? '-'}</td>
        `;
        tabelaCorpo.appendChild(row);
    });
}

function ordenarTabela(colunaIndex) {
    const colunas = ["ID", "COD_FOR", "DESCRICAO", "NOME_FAN", "CNPJ", "INSC_EST", "INSC_MUN", "SISTEMA"];
    const colunaChave = colunas[colunaIndex]; // Ajuste para index correto

    if (!colunaChave) return; // Evita erro ao clicar no checkbox

    // Alterna entre crescente e decrescente
    ordenacao[colunaChave] = !ordenacao[colunaChave];

    // Remove classes anteriores de ordenação
    document.querySelectorAll("th").forEach(th => th.classList.remove('sorted-asc', 'sorted-desc'));

    // Adiciona a classe de ordenação para a coluna atual
    const th = document.querySelectorAll("th")[colunaIndex];
    th.classList.add(ordenacao[colunaChave] ? 'sorted-asc' : 'sorted-desc');

    transportadoras.sort((a, b) => {
        let valorA = a[colunaChave] ?? '';
        let valorB = b[colunaChave] ?? '';

        if (!isNaN(valorA) && !isNaN(valorB)) {
            valorA = Number(valorA);
            valorB = Number(valorB);
        } else {
            valorA = valorA.toString().toLowerCase();
            valorB = valorB.toString().toLowerCase();
        }

        return ordenacao[colunaChave] ? valorA.localeCompare(valorB) : valorB.localeCompare(valorA);
    });

    renderizarTabela(transportadoras);
}

function formatarCNPJ(cnpj) {
    // Verifica se o CNPJ é nulo ou indefinido
    if (!cnpj) return '-';

    // Garantir que o CNPJ seja uma string
    cnpj = String(cnpj);

    // Remove todos os caracteres não numéricos (como pontos, barras e hífens)
    cnpj = cnpj.replace(/\D/g, '');

    // Se o CNPJ tem menos de 14 dígitos, adiciona zeros à esquerda
    cnpj = cnpj.padStart(14, '0');

    // Se o CNPJ ainda não tiver 14 dígitos, retorna '-'
    if (cnpj.length !== 14) return '-';

    // Formata o CNPJ no formato "XX.XXX.XXX/XXXX-XX"
    return cnpj.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, "$1.$2.$3/$4-$5");
}

// Função para exibir o balão de notificação (toast)
function exibirMensagem(texto, tipo, recarregar = false) {
    const toastContainer = document.getElementById('toast-container');

    if (!toastContainer) {
        console.error('Elemento #toast-container não encontrado.');
        return;
    }

    let toast = document.createElement('div');
    toast.className = `toast-message ${tipo}`;
    toast.textContent = texto;
    
    toastContainer.appendChild(toast);

    // Exibir o balão por 2 segundos antes de removê-lo
    setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => {
            toast.remove();
            if (recarregar) {
                location.reload(); // Recarrega a página só depois do fade-out
            }
        }, 500);
    }, 2000);
}