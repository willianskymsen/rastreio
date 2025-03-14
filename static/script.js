// Função para carregar a lista de arquivos XML
function carregarArquivos() {
    const fileList = document.getElementById('fileList');
    fileList.innerHTML = '<div class="loading"><div class="spinner"></div><p>Carregando documentos fiscais...</p></div>';

    // Adicionar tempo mínimo de exibição do loading para evitar flash de conteúdo
    const startTime = new Date().getTime();
    const minLoadTime = 700; // milissegundos

    fetch('/api/arquivos')
        .then(response => {
            if (!response.ok) {
                throw new Error('Falha na conexão com o servidor');
            }
            return response.json();
        })
        .then(files => {
            // Garantir tempo mínimo de loading
            const elapsedTime = new Date().getTime() - startTime;
            const remainingTime = Math.max(0, minLoadTime - elapsedTime);

            setTimeout(() => {
                renderizarArquivos(files);
            }, remainingTime);
        })
        .catch(error => {
            console.error('Erro ao carregar arquivos:', error);

            setTimeout(() => {
                fileList.innerHTML = `
                    <div class="error">
                        <i class="fas fa-exclamation-triangle"></i>
                        <p>Não foi possível carregar a lista de documentos. Verifique sua conexão ou tente novamente mais tarde.</p>
                    </div>
                `;
            }, Math.max(0, minLoadTime - (new Date().getTime() - startTime)));
        });
}

// Função para renderizar a lista de arquivos
function renderizarArquivos(files) {
    const fileList = document.getElementById('fileList');

    if (files.length === 0) {
        fileList.innerHTML = `
            <div class="empty-state">
                <i class="far fa-folder-open"></i>
                <p>Nenhum documento fiscal disponível</p>
                <small>Os documentos fiscais aparecerão aqui quando estiverem disponíveis</small>
            </div>
        `;
    } else {
        // Ordenar arquivos por número da NF decrescente
        files.sort((a, b) => b.nNF - a.nNF);

        // Renderizar a lista de arquivos
        fileList.innerHTML = files.map(file => `
            <li>
                <a href="#" class="fileLink" data-filename="${file.filename}">
                    <i class="fas fa-file-invoice-dollar"></i>
                    <div>
                        <strong>NF-e: ${file.nNF}</strong>
                        ${file.data ? `<div class="file-date">${file.data}</div>` : ''}
                    </div>
                </a>
            </li>
        `).join('');

        // Adiciona eventos aos links
        document.querySelectorAll('.fileLink').forEach(link => {
            link.addEventListener('click', function(event) {
                event.preventDefault();
                // Remove classe ativa de todos os itens
                document.querySelectorAll('.fileLink').forEach(l => l.classList.remove('active'));
                // Adiciona classe ativa ao item clicado
                this.classList.add('active');

                const filename = this.getAttribute('data-filename');
                buscarDados(filename);
            });
        });

        // Seleciona automaticamente o primeiro item da lista
        if (files.length > 0) {
            const firstLink = document.querySelector('.fileLink');
            if (firstLink) {
                firstLink.classList.add('active');
                buscarDados(firstLink.getAttribute('data-filename'));
            }
        }
    }
}

// Função para formatar data e hora
function formatarDataHora(dataHoraString) {
    if (!dataHoraString) return '';

    try {
        const data = new Date(dataHoraString);
        return new Intl.DateTimeFormat('pt-BR', {
            day: '2-digit',
            month: '2-digit',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }).format(data);
    } catch (e) {
        return dataHoraString;
    }
}

// Função para determinar a classe de status com base no tipo do evento
function determinarClasseEvento(item) {
    if (item.tipo === 'entrega' && (
        item.ocorrencia.toLowerCase().includes('entregue') ||
        item.ocorrencia.toLowerCase().includes('finaliz')
    )) {
        return 'event-entregue';
    } else if (
        item.ocorrencia.toLowerCase().includes('problema') ||
        item.ocorrencia.toLowerCase().includes('devol') ||
        item.ocorrencia.toLowerCase().includes('recusa') ||
        item.ocorrencia.toLowerCase().includes('ausente')
    ) {
        return 'event-problema';
    }
    return 'event-transito';
}

// Função para buscar dados de rastreamento
function buscarDados(filename) {
    if (!filename) return;

    const resultDiv = document.getElementById('result');
    resultDiv.innerHTML = '<div class="loading"><div class="spinner"></div><p>Carregando dados de rastreamento...</p></div>';

    // Adicionar tempo mínimo de exibição do loading
    const startTime = new Date().getTime();
    const minLoadTime = 800; // milissegundos

    fetch('/api/dados', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ filename: filename })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Falha na comunicação com o servidor');
        }
        return response.json();
    })
    .then(data => {
        // Garantir tempo mínimo de loading
        const elapsedTime = new Date().getTime() - startTime;
        const remainingTime = Math.max(0, minLoadTime - elapsedTime);

        setTimeout(() => {
            renderizarDados(data, filename);
        }, remainingTime);
    })
    .catch(error => {
        console.error('Erro:', error);

        setTimeout(() => {
            resultDiv.innerHTML = `
                <div class="error">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Não foi possível carregar os dados de rastreamento. Tente novamente ou contate o suporte.</p>
                </div>
            `;
        }, Math.max(0, minLoadTime - (new Date().getTime() - startTime)));
    });
}

// Função para renderizar os dados
function renderizarDados(data, filename) {
    const resultDiv = document.getElementById('result');

    if (data.error) {
        resultDiv.innerHTML = `
            <div class="error">
                <i class="fas fa-exclamation-triangle"></i>
                <p>${data.error}</p>
            </div>
        `;
        return;
    }

    // Ordenar eventos por ordem cronológica decrescente, com "MERCADORIA ENTREGUE" sempre primeiro
    if (data.items && data.items.length > 0) {
        data.items.sort((a, b) => {
            const isEntregaA = a.ocorrencia.toLowerCase().includes('mercadoria entregue');
            const isEntregaB = b.ocorrencia.toLowerCase().includes('mercadoria entregue');

            // Se A for "MERCADORIA ENTREGUE" e B não for, A vem primeiro
            if (isEntregaA && !isEntregaB) return -1;
            // Se B for "MERCADORIA ENTREGUE" e A não for, B vem primeiro
            if (isEntregaB && !isEntregaA) return 1;

            // Se ambos forem ou não forem "MERCADORIA ENTREGUE", ordena por data decrescente
            const dataA = new Date(a.data_hora);
            const dataB = new Date(b.data_hora);
            return dataB - dataA;
        });
    }

    // Identificar o status atual com base no evento mais recente
    let statusAtual = 'Em processamento';
    let statusIcone = 'fas fa-clock';
    let statusClasse = 'status-processing';

    if (data.items && data.items.length > 0) {
        const ultimoEvento = data.items[0];

        if (ultimoEvento.ocorrencia.toLowerCase().includes('entregue')) {
            statusAtual = 'Entregue';
            statusIcone = 'fas fa-check-circle';
            statusClasse = 'status-delivered';
        } else if (ultimoEvento.ocorrencia.toLowerCase().includes('problema')) {
            statusAtual = 'Problema na entrega';
            statusIcone = 'fas fa-exclamation-circle';
            statusClasse = 'status-problem';
        } else if (ultimoEvento.tipo === 'transito') {
            statusAtual = 'Em trânsito';
            statusIcone = 'fas fa-truck';
            statusClasse = 'status-transit';
        }
    }

    // Encontrar a primeira data do rastreio (data mais antiga)
    let primeiraDataRastreio = null;
    if (data.items && data.items.length > 0) {
        // Ordena os eventos por data crescente para encontrar a mais antiga
        const eventosOrdenadosCrescente = [...data.items].sort((a, b) => {
            const dataA = new Date(a.data_hora);
            const dataB = new Date(b.data_hora);
            return dataA - dataB; // Crescente (mais antiga primeiro)
        });
        primeiraDataRastreio = eventosOrdenadosCrescente[0].data_hora;
    }

    // Encontrar a data de entrega (último evento de entrega)
    let dataEntrega = null;
    if (data.items && data.items.length > 0) {
        const eventoEntrega = data.items.find(item =>
            item.ocorrencia.toLowerCase().includes('mercadoria entregue')
        );
        if (eventoEntrega) {
            dataEntrega = eventoEntrega.data_hora;
        }
    }

    // Calcular o tempo de transporte (dias entre emissão e entrega)
    let tempoTransporte = null;
    if (primeiraDataRastreio && dataEntrega) {
        const dataEmissao = new Date(primeiraDataRastreio);
        const dataEntregaObj = new Date(dataEntrega);
        const diferencaMs = dataEntregaObj - dataEmissao; // Diferença em milissegundos
        tempoTransporte = Math.floor(diferencaMs / (1000 * 60 * 60 * 24)); // Converter para dias
    }

    // Formatar a exibição dos eventos
    const formattedEvents = data.items && data.items.length > 0
        ? data.items.map(item => {
            const eventClass = determinarClasseEvento(item);
            const dataFormatada = formatarDataHora(item.data_hora);

            return `
                <div class="event-item ${eventClass}">
                    <div class="event-header">
                        <div class="event-date"><i class="far fa-calendar-alt"></i> ${dataFormatada}</div>
                        <div><span class="badge">${item.tipo.toUpperCase()}</span></div>
                    </div>
                    <div class="event-title">${item.ocorrencia}</div>
                    <div class="event-description">${item.descricao || ''}</div>
                    ${item.nome_recebedor ? `
                    <div class="event-detail">
                        <i class="far fa-user"></i>
                        <span>Recebedor: ${item.nome_recebedor}</span>
                        ${item.documento_recebedor ? `<span>Documento: ${item.documento_recebedor}</span>` : ''}
                    </div>` : ''}
                    ${item.local ? `
                    <div class="event-detail">
                        <i class="fas fa-map-marker-alt"></i>
                        <span>${item.local}</span>
                    </div>` : ''}
                </div>
            `;
        }).join('')
        : `<div class="empty-state"><i class="fas fa-info-circle"></i><p>Ainda não há eventos de rastreamento para este documento</p></div>`;

    resultDiv.innerHTML = `
        <div class="result-header">
            <h2><i class="fas fa-truck-loading"></i> Rastreamento da NF-e</h2>
            <div class="status ${statusClasse}">
                <i class="${statusIcone}"></i>
                <span>${statusAtual}</span>
            </div>
        </div>

        <div class="nf-info">
            <div>
                <div class="info-label">Destinatário</div>
                <div class="info-value">${data.destinatario}</div>
            </div>
            <div>
                <div class="info-label">Número NF-e</div>
                <div class="info-value">${data.nNF}</div>
            </div>
            <div>
                <div class="info-label">Emissão</div>
                <div class="info-value">${primeiraDataRastreio ? formatarDataHora(primeiraDataRastreio) : '--/--/----'}</div>
            </div>
            <div>
                <div class="info-label">Data de Entrega</div>
                <div class="info-value">${dataEntrega ? formatarDataHora(dataEntrega) : '--/--/----'}</div>
            </div>
            <div>
                <div class="info-label">Tempo de Transporte</div>
                <div class="info-value">${tempoTransporte !== null ? `${tempoTransporte} dia(s)` : '--'}</div>
            </div>
        </div>

        <h3><i class="fas fa-history"></i> Histórico de Eventos</h3>
        <div class="events-list">
            ${formattedEvents}
        </div>
    `;

    // Adicionar rolagem suave ao carregar os dados
    window.requestAnimationFrame(() => {
        const eventsDiv = document.querySelector('.events-list');
        if (eventsDiv) {
            eventsDiv.scrollTop = 0;
        }
    });
}

// Inicialização ao carregar a página
document.addEventListener('DOMContentLoaded', () => {
    carregarArquivos();

    // Adicionar botão de atualização se necessário
    const header = document.querySelector('.sidebar h2');
    if (header) {
        const refreshButton = document.createElement('button');
        refreshButton.className = 'refresh-btn';
        refreshButton.innerHTML = '<i class="fas fa-sync-alt"></i>';
        refreshButton.title = 'Atualizar lista';
        refreshButton.addEventListener('click', (e) => {
            e.preventDefault();
            carregarArquivos();
        });
        header.appendChild(refreshButton);
    }
});