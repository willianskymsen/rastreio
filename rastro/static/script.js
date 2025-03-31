// ==============================================
// CONSTANTES E CONFIGURAÇÕES
// ==============================================
const STATUS_CONFIG = {
  ENTREGUE: { 
    icon: 'fa-check-circle', 
    color: '#2ecc71', 
    title: 'Entregues', 
    order: 1 
  },
  EM_TRANSITO: { 
    icon: 'fa-truck', 
    color: '#3498db', 
    title: 'Em Trânsito', 
    order: 2 
  },
  PROBLEMA: { 
    icon: 'fa-exclamation-triangle', 
    color: '#e74c3c', 
    title: 'Com Problema', 
    order: 3 
  },
  TOTAL: { 
    icon: 'fa-list-alt', 
    color: '#95a5a6', 
    title: 'Total', 
    order: 4 
  }
};

const STATUS_INFO = {
  ENTREGUE: {
    text: "Entregue",
    icon: "fas fa-check-circle",
    class: "status-delivered"
  },
  PROBLEMA: {
    text: "Problema",
    icon: "fas fa-exclamation-circle",
    class: "status-problem"
  },
  EM_TRANSITO: {
    text: "Em trânsito",
    icon: "fas fa-truck",
    class: "status-transit"
  },
  NAO_ENCONTRADO: {
    text: "Não encontrado",
    icon: "fas fa-question-circle",
    class: "status-unknown"
  }
};

// ==============================================
// FUNÇÕES PRINCIPAIS
// ==============================================

/**
 * Carrega a lista de arquivos XML da API
 */
async function carregarArquivos() {
  try {
    const response = await fetch("/rastro/rastro/api/arquivos");
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    const data = await response.json();
    if (!data || data.length === 0) {
      mostrarMensagemSemDados();
      return;
    }
    
    const statusData = calcularStatusData(data);
    renderizarArquivos(data, statusData);
    
  } catch (error) {
    console.error("Erro ao carregar arquivos:", error);
    mostrarErroCarregamento(error);
  }
}

/**
 * Renderiza a lista de arquivos e os cards de status
 */
function renderizarArquivos(files, statusData) {
  renderizarStatusCards(statusData);
  renderizarListaArquivos(files);
  configurarEventListeners();
  selecionarItensPadrao();
}

/**
 * Busca dados de rastreamento para uma NF-e específica
 */
async function buscarDados(numNf) {
  if (!numNf) return;

  mostrarLoaderRastreamento();
  const startTime = Date.now();
  const minLoadTime = 800;

  try {
    const response = await fetch("/rastro/rastro/api/dados", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename: numNf })
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.error || "Falha na comunicação com o servidor");
    }

    if (data.status === "NAO_ENCONTRADO") {
      throw new Error("NF-e não encontrada na base de rastreamento");
    }

    const elapsedTime = Date.now() - startTime;
    setTimeout(
      () => renderizarDados(data, numNf),
      Math.max(0, minLoadTime - elapsedTime)
    );

  } catch (error) {
    console.error("Erro:", error);
    const elapsedTime = Date.now() - startTime;
    setTimeout(
      () => mostrarErroRastreamento(error, numNf),
      Math.max(0, minLoadTime - elapsedTime)
    );
  }
}

// ==============================================
// FUNÇÕES DE RENDERIZAÇÃO (ATUALIZADAS)
// ==============================================

/**
 * Renderiza os cards de status usando templates
 */
function renderizarStatusCards(statusData) {
  const container = document.getElementById("statusCardsContainer");
  container.innerHTML = '';

  Object.entries(STATUS_CONFIG)
    .sort(([a], [b]) => STATUS_CONFIG[a].order - STATUS_CONFIG[b].order)
    .forEach(([status, config]) => {
      const template = document.getElementById("statusCardTemplate").content.cloneNode(true);
      const card = template.querySelector('.status-card');
      
      card.dataset.status = status;
      
      const iconElement = card.querySelector('.status-card-icon');
      iconElement.style.color = config.color;
      iconElement.querySelector('i').className = `fas ${config.icon}`;
      
      card.querySelector('.status-card-title').textContent = config.title;
      card.querySelector('.status-card-count').textContent = statusData[status] || 0;
      
      container.appendChild(template);
    });
}

/**
 * Renderiza a lista de arquivos usando templates
 */
function renderizarListaArquivos(files) {
  const filesList = document.getElementById("fileList");
  window.currentFiles = files || [];
  filesList.innerHTML = '';

  if (!files || files.length === 0) {
    filesList.innerHTML = criarMensagemVazia("Nenhum documento encontrado", "fa-file-alt");
    return;
  }

  files.forEach(file => {
    const template = document.getElementById("fileItemTemplate").content.cloneNode(true);
    const item = template.querySelector('.file-item');
    
    item.dataset.status = file.status || '';
    item.querySelector('.file-num').textContent = file.NUM_NF;
    
    const statusElement = item.querySelector('.file-status');
    const statusText = file.status === 'EM_TRANSITO' ? 'Em trânsito' : 
                      file.status === 'ENTREGUE' ? 'Entregue' : 
                      file.status === 'PROBLEMA' ? 'Problema' : 
                      file.status || 'Sem status';
    statusElement.textContent = statusText;
    
    if (file.status) {
      statusElement.className = `file-status status-${file.status.toLowerCase().replace('_', '')}`;
    }

    // Adicionar ícone baseado no status
    const fileIcon = item.querySelector('.file-icon i');
    if (file.status === 'ENTREGUE') {
      fileIcon.className = 'fas fa-check-circle';
    } else if (file.status === 'EM_TRANSITO') {
      fileIcon.className = 'fas fa-truck';
    } else if (file.status === 'PROBLEMA') {
      fileIcon.className = 'fas fa-exclamation-triangle';
    } else {
      fileIcon.className = 'fas fa-file-invoice'; // Padrão para documentos sem status específico
    }
    
    item.querySelector('.transportadora').textContent = file.transportadora || 'Transportadora não informada';
    item.querySelector('.local').textContent = `${file.cidade || 'Local desconhecido'}${file.uf ? '/' + file.uf : ''}`;
    
    filesList.appendChild(template);
  });
}

/**
 * Renderiza os dados de rastreamento usando templates
 */
function renderizarDados(data, numNf) {
  const resultDiv = document.getElementById("result");
  const template = document.getElementById("trackingTemplate").content.cloneNode(true);
  
  // Preencher dados básicos
  template.querySelector('.nf-number').textContent = numNf;
  template.querySelector('.remetente').textContent = data.dados?.remetente || "--";
  template.querySelector('.destinatario').textContent = data.dados?.destinatario || "--";
  
  // Preencher status
  const statusInfo = STATUS_INFO[data.status_entrega] || {
    text: "Em processamento",
    icon: "fas fa-clock",
    class: "status-processing"
  };
  
  const statusBadge = template.querySelector('.status-badge');
  statusBadge.className = `status-badge ${statusInfo.class}`;
  statusBadge.querySelector('i').className = statusInfo.icon;
  statusBadge.querySelector('.status-text').textContent = statusInfo.text;
  
  // Adicionar metadados adicionais
  const { primeiroEvento, eventoEntrega, tempoTransporte } = calcularTemposTransporte(data.dados?.items || []);
  
  const metaGrid = template.querySelector('.tracking-meta-grid');
  if (primeiroEvento) {
    metaGrid.appendChild(criarMetaItem("Primeiro evento", formatarDataHora(primeiroEvento.data_hora), "fa-flag"));
  }
  if (eventoEntrega) {
    metaGrid.appendChild(criarMetaItem("Entrega", formatarDataHora(eventoEntrega.data_hora), "fa-check-circle"));
  }
  if (tempoTransporte !== null) {
    metaGrid.appendChild(criarMetaItem("Tempo transporte", `${tempoTransporte} dia(s)`, "fa-clock"));
  }
  
  // Limpar e preencher resultDiv
  resultDiv.innerHTML = '';
  resultDiv.appendChild(template);
  
  // Adicionar eventos à timeline
  if (data.dados?.items?.length) {
    const timelineContainer = resultDiv.querySelector('.timeline-container');
    data.dados.items
      .sort((a, b) => new Date(b.data_hora) - new Date(a.data_hora))
      .forEach(item => adicionarEventoTimeline(timelineContainer, item));
  }
}

/**
 * Cria um item de meta informação para o grid
 */
function criarMetaItem(label, value, icon) {
  const template = document.createElement('div');
  template.className = 'meta-item';
  template.innerHTML = `
    <div class="meta-label"><i class="fas ${icon}"></i> ${label}</div>
    <div class="meta-value">${value}</div>
  `;
  return template;
}

/**
 * Adiciona um evento à timeline
 */
function adicionarEventoTimeline(container, item) {
  const template = document.getElementById("eventItemTemplate").content.cloneNode(true);
  const event = template.querySelector('.timeline-event');
  
  // Configurar classe do evento com base no tipo
  const eventClass = determinarClasseEvento(item);
  event.classList.add(eventClass);

  // Configurar ícone baseado no tipo de evento
  const eventMarker = event.querySelector('.event-marker i');
  if (eventClass === 'event-entregue') {
    eventMarker.className = 'fas fa-check-circle';
  } else if (eventClass === 'event-problema') {
    eventMarker.className = 'fas fa-exclamation-triangle';
  } else if (eventClass === 'event-emissao') {
    eventMarker.className = 'fas fa-file-alt';
  } else if (eventClass === 'event-coleta') {
    eventMarker.className = 'fas fa-truck-pickup';
  } else if (eventClass === 'event-chegada') {
    eventMarker.className = 'fas fa-warehouse';
  } else if (eventClass === 'event-saida') {
    eventMarker.className = 'fas fa-truck-moving';
  } else {
    eventMarker.className = 'fas fa-truck'; // Default para outros eventos
  } 
  
  // Preencher dados do evento
  event.querySelector('.event-time').textContent = formatarDataHora(item.data_hora);
  if (item.tipo) {
    event.querySelector('.event-type').textContent = item.tipo.toUpperCase();
  }
  event.querySelector('.event-title').textContent = item.ocorrencia;
  
  // Adicionar descrição se existir
  if (item.descricao) {
    const desc = document.createElement('p');
    desc.className = 'event-description';
    desc.textContent = item.descricao;
    event.querySelector('.event-content').appendChild(desc);
  }
  
  // Adicionar detalhes dinâmicos
  const detailsContainer = event.querySelector('.event-details');
  
  if (item.cidade) {
    detailsContainer.appendChild(criarDetailItem('map-marker-alt', 
      `${item.cidade}${item.filial ? ` (${item.filial})` : ''}`));
  }
  
  if (item.dominio) {
    detailsContainer.appendChild(criarDetailItem('truck', item.dominio));
  }
  
  if (item.nome_recebedor) {
    const text = `Recebido por: ${item.nome_recebedor}${item.nro_doc_recebedor ? ` (${item.nro_doc_recebedor})` : ''}`;
    detailsContainer.appendChild(criarDetailItem('user', text));
  }
  
  container.appendChild(template);
}

/**
 * Cria um item de detalhe para o evento
 */
function criarDetailItem(icon, text) {
  const div = document.createElement('div');
  div.className = 'detail-item';
  div.innerHTML = `<i class="fas fa-${icon}"></i> <span>${text}</span>`;
  return div;
}

// ==============================================
// FUNÇÕES AUXILIARES (MANTIDAS)
// ==============================================

function criarMensagemVazia(mensagem, icone = "fa-info-circle") {
  return `
    <div class="empty-state">
      <i class="fas ${icone}"></i>
      <p>${mensagem}</p>
    </div>`;
}

function mostrarLoaderRastreamento() {
  const resultDiv = document.getElementById("result");
  resultDiv.innerHTML = `
    <div class="loading">
      <div class="spinner"></div>
      <p>Carregando dados...</p>
    </div>`;
}

function mostrarErroRastreamento(error, numNf) {
  const resultDiv = document.getElementById("result");
  resultDiv.innerHTML = `
    <div class="error">
      <i class="fas fa-exclamation-triangle"></i>
      <p>${error.message || "Erro ao carregar dados"}</p>
      <button onclick="buscarDados('${numNf}')" class="retry-btn">
        <i class="fas fa-sync-alt"></i> Tentar novamente
      </button>
    </div>`;
}

function mostrarMensagemSemDados() {
  document.getElementById("fileList").innerHTML = criarMensagemVazia(
    "Nenhum documento encontrado na base de dados",
    "fa-info-circle"
  );
}

function mostrarErroCarregamento(error) {
  document.getElementById("fileList").innerHTML = `
    <div class="error">
      <i class="fas fa-exclamation-triangle"></i>
      <p>Falha ao carregar documentos</p>
      <small>${error.message}</small>
    </div>`;
}

function calcularStatusData(files) {
  const entregue = files.filter(item => item.status === 'ENTREGUE').length;
  const emTransito = files.filter(item => item.status === 'EM_TRANSITO').length;
  
  return {
    ENTREGUE: entregue,
    EM_TRANSITO: emTransito,
    TOTAL: entregue + emTransito  // Só soma ENTREGUE + EM_TRANSITO
  };
}

function calcularTemposTransporte(items) {
  const primeiroEvento = items[items.length - 1];
  const eventoEntrega = items.find(e => e.ocorrencia.toLowerCase().includes("entregue"));
  
  let tempoTransporte = null;
  if (primeiroEvento?.data_hora && eventoEntrega?.data_hora) {
    const diffMs = new Date(eventoEntrega.data_hora) - new Date(primeiroEvento.data_hora);
    tempoTransporte = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  }
  
  return { primeiroEvento, eventoEntrega, tempoTransporte };
}

function formatarDataHora(dataHora) {
  if (!dataHora) return "";
  try {
    return new Intl.DateTimeFormat("pt-BR", {
      day: "2-digit",
      month: "2-digit",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit"
    }).format(new Date(dataHora));
  } catch {
    return dataHora;
  }
}

function determinarClasseEvento(item) {
  if (!item?.ocorrencia) return "event-transito";
  const oc = item.ocorrencia.toLowerCase();
  
  if (oc.includes("entregue") || oc.includes("entrega realizada")) return "event-entregue";
  if (oc.includes("problema") || oc.includes("devol") || oc.includes("recusa") || oc.includes("cancelado")) return "event-problema";
  if (oc.includes("emissão") || oc.includes("emitido")) return "event-emissao";
  if (oc.includes("coleta") || oc.includes("retirada")) return "event-coleta";
  if (oc.includes("chegada") || oc.includes("chegou")) return "event-chegada";
  if (oc.includes("saída") || oc.includes("saiu")) return "event-saida";
  if (oc.includes("alfândega") || oc.includes("fiscal")) return "event-customs";
  if (oc.includes("inspeção") || oc.includes("vistoria")) return "event-inspecao";
  
  return "event-transito";
}

// ==============================================
// CONFIGURAÇÃO DE EVENTOS
// ==============================================

function configurarEventListeners() {
  configurarEventosCardsStatus();
  configurarEventosItensArquivo();
  configurarInputBusca();
}

function configurarEventosCardsStatus() {
  document.addEventListener('click', function(e) {
    const card = e.target.closest('.status-card');
    if (!card) return;
    
    document.querySelectorAll('.status-card').forEach(c => {
      c.classList.remove('active');
      c.setAttribute('aria-current', 'false');
    });
    
    card.classList.add('active');
    card.setAttribute('aria-current', 'true');
    
    const status = card.getAttribute('data-status');
    const searchTerm = document.getElementById('searchNfe').value.toLowerCase();
    filtrarArquivos(window.currentFiles, searchTerm, status === 'TOTAL' ? '' : status);
  });
}

function configurarEventosItensArquivo() {
  document.addEventListener('click', function(e) {
    const item = e.target.closest('.file-item');
    if (!item) return;
    
    document.querySelectorAll('.file-item').forEach(i => {
      i.classList.remove('active');
      i.setAttribute('aria-selected', 'false');
    });
    
    item.classList.add('active');
    item.setAttribute('aria-selected', 'true');
    buscarDados(item.querySelector('.file-num').textContent);
  });
}

function configurarInputBusca() {
  document.getElementById('searchNfe').addEventListener('input', (e) => {
    const searchTerm = e.target.value.toLowerCase();
    const activeStatus = document.querySelector('.status-card.active')?.getAttribute('data-status') || '';
    filtrarArquivos(window.currentFiles, searchTerm, activeStatus === 'TOTAL' ? '' : activeStatus);
  });
}

function filtrarArquivos(files, searchTerm = "", status = "") {
  const filtered = files.filter(file => 
    (String(file.NUM_NF).toLowerCase().includes(searchTerm.toLowerCase()) || 
     String(file.transportadora || "").toLowerCase().includes(searchTerm.toLowerCase())) &&
    (!status || (file.status || "").toUpperCase() === status)
  );

  const filesList = document.getElementById("fileList");
  filesList.innerHTML = filtered.length > 0 
    ? filtered.map(file => {
        const template = document.getElementById("fileItemTemplate").content.cloneNode(true);
        const item = template.querySelector('.file-item');
        const statusText = file.status === 'EM_TRANSITO' ? 'Em trânsito' : 
                          file.status === 'ENTREGUE' ? 'Entregue' : 
                          file.status === 'PROBLEMA' ? 'Problema' : 
                          file.status || 'Sem status';
        item.dataset.status = file.status || '';
        item.querySelector('.file-num').textContent = file.NUM_NF;
        item.querySelector('.file-status').textContent = statusText;
        item.querySelector('.transportadora').textContent = file.transportadora || 'Transportadora não informada';
        item.querySelector('.local').textContent = `${file.cidade || 'Local desconhecido'}${file.uf ? '/' + file.uf : ''}`;
        return item.outerHTML;
      }).join('')
    : criarMensagemVazia("Nenhum documento encontrado", "fa-folder-open");

  configurarEventosItensArquivo();
}

// ==============================================
// INICIALIZAÇÃO
// ==============================================

function selecionarItensPadrao() {
  const emTransitoCard = document.querySelector('.status-card[data-status="EM_TRANSITO"]') || 
                        document.querySelector('.status-card');
  if (emTransitoCard) emTransitoCard.click();

  const firstFileItem = document.querySelector('.file-item');
  if (firstFileItem) firstFileItem.click();
}

document.addEventListener("DOMContentLoaded", function() {
  carregarArquivos();
});