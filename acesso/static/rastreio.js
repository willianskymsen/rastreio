document.addEventListener("DOMContentLoaded", function () {
  const trackingCodeElement = document.getElementById("tracking-code");
  const remessaInfoCard = document.getElementById("remessa-info-card");
  const remessaStatus = document.getElementById("remessa-status");
  const destinatarioInfo = document.getElementById("destinatario-info");
  const destinatarioSpan = document.getElementById("destinatario");
  const remetenteInfo = document.getElementById("remetente-info");
  const remetenteSpan = document.getElementById("remetente");
  const pesoInfo = document.getElementById("peso-info");
  const pesoBrtSpan = document.getElementById("peso-brt");
  const volumesInfo = document.getElementById("volumes-info");
  const volumesSpan = document.getElementById("volumes");
  const dataPostagemInfo = document.getElementById("data-postagem-info");
  const dataPostagemSpan = document.getElementById("data-postagem");
  const previsaoEntregaInfo = document.getElementById("previsao-entrega-info");
  const previsaoEntregaSpan = document.getElementById("previsao-entrega");
  const tipoServicoInfo = document.getElementById("tipo-servico-info");
  const tipoServicoSpan = document.getElementById("tipo-servico");
  const modalidadeInfo = document.getElementById("modalidade-info");
  const modalidadeSpan = document.getElementById("modalidade");
  const camposAdicionaisContainer = document.getElementById(
    "campos-adicionais-container"
  );
  const historyContainer = document.getElementById(
    "tracking-history-container"
  );
  const currentYearSpan = document.getElementById("current-year");
  const filterEvents = document.getElementById("filter-events");
  const progressIndicator = document.getElementById("progress-indicator");
  const progressSteps = document.querySelectorAll(".progress-step");
  const printButton = document.getElementById("print-button");
  const urlParams = new URLSearchParams(window.location.search);
  const chave = urlParams.get("chave");
  const shareButton = document.getElementById("share-button");
  const shareModal = document.getElementById("share-modal");
  const closeModal = document.querySelector(".close-modal");
  const shareUrlInput = document.getElementById("share-url");
  const copyUrlBtn = document.getElementById("copy-url-btn");
  const copyFeedback = document.getElementById("copy-feedback");
  const whatsappShareBtn = document.getElementById("whatsapp-share-btn");
  const emailShareBtn = document.getElementById("email-share-btn");
  const smsShareBtn = document.getElementById("sms-share-btn");

  // Informações para compartilhamento
  const currentUrl = window.location.href;
  const shareText = `👋 Olá!

    Acompanhe o status da sua encomenda Skymsen:

    📦 Seu rastreamento: ${currentUrl}

    📌 Fique por dentro de cada etapa da entrega!`;
  const emailSubject = "Rastreamento de Encomenda Skymsen";
  const emailBody = `Olá!

        Acompanhe o status da sua encomenda Skymsen em tempo real: ${currentUrl}

        Mantenha-se atualizado sobre cada etapa da sua entrega.

        Atenciosamente,
        Equipe Skymsen`;
  const smsText = `Skymsen: Acompanhe sua encomenda: ${currentUrl}`;

  console.log("Botão de compartilhar:", shareButton);
  console.log("Modal de compartilhamento:", shareModal);

  function isMobile() {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(
      navigator.userAgent
    );
  }

  // Esconder botão SMS em computadores
  if (!isMobile() && smsShareBtn) {
    smsShareBtn.style.display = "none";
  }

  // Configuração modal
  if (shareButton) {
    shareButton.addEventListener("click", function () {
      console.log("Botão de compartilhar foi clicado!");
      shareModal.style.display = "flex";
      shareModal.style.opacity = "1"; // Adicione isso para testar
      shareModal.style.visibility = "visible"; // Adicione isso para testar
      shareUrlInput.value = currentUrl;
      copyFeedback.classList.remove("show");
    });
  }

  if (closeModal) {
    closeModal.addEventListener("click", function () {
      shareModal.style.display = "none";
    });
  }

  window.addEventListener("click", function (event) {
    if (event.target === shareModal) {
      shareModal.style.display = "none";
    }
  });

  window.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && shareModal.style.display === "flex") {
      event.preventDefault();
      shareModal.style.display = "none";
    }
  });

  if (copyUrlBtn) {
    copyUrlBtn.addEventListener("click", function () {
      shareUrlInput.select();

      // Usando a nova API Clipboard quando disponível
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard
          .writeText(shareUrlInput.value)
          .then(() => {
            showCopyFeedback();
          })
          .catch(() => {
            // Fallback para o método antigo
            document.execCommand("copy");
            showCopyFeedback();
          });
      } else {
        // Método antigo para navegadores que não suportam a API Clipboard
        document.execCommand("copy");
        showCopyFeedback();
      }
    });
  }

  function showCopyFeedback() {
    copyFeedback.classList.add("show");
    setTimeout(() => {
      copyFeedback.classList.remove("show");
    }, 2000);
  }

  // Compartilhar no WhatsApp
  if (!isMobile() && whatsappShareBtn) {
    let firstClickTime = 0;
    const doubleClickThreshold = 500; // Tempo em milissegundos para considerar um "segundo clique rápido"

    whatsappShareBtn.addEventListener("click", function () {
      const currentTime = new Date().getTime();
      const shareTextEncoded = encodeURIComponent(shareText);
      const whatsappUrlApp = `whatsapp://send?text=${shareTextEncoded}`;
      const whatsappUrlWeb = `https://web.whatsapp.com/send?text=${shareTextEncoded}`;

      if (currentTime - firstClickTime > doubleClickThreshold) {
        // Primeiro clique (ou clique após um certo intervalo) - tenta abrir o desktop
        window.open(whatsappUrlApp);
        firstClickTime = currentTime;
      } else {
        // Segundo clique rápido - abre o web
        window.open(whatsappUrlWeb, "_blank");
        firstClickTime = 0; // Reseta
      }
    });
  }

  // Compartilhar por Email
  if (emailShareBtn) {
    console.log("Botão de email encontrado e listener sendo adicionado.");
    emailShareBtn.addEventListener("click", function () {
      alert('Ao clicar em "OK", seu programa de email padrão será aberto.');
      const emailShareUrl = `mailto:?subject=${encodeURIComponent(
        emailSubject
      )}&body=${emailBody}`;
      console.log("URL de email:", emailShareUrl); // Adicione esta linha
      window.location.href = emailShareUrl;
    });
  }

  // Compartilhar por SMS (apenas em dispositivos móveis)
  if (smsShareBtn) {
    smsShareBtn.addEventListener("click", function () {
      if (isMobile()) {
        const smsShareUrl = `sms:?body=${encodeURIComponent(smsText)}`;
        window.location.href = smsShareUrl;
      }
    });
  }

  // Botão de impressão para gerar PDF
  printButton.addEventListener("click", function () {
    const originalElement = document.getElementById("container-para-imprimir");
    const trackingCode = document.getElementById("tracking-code").textContent;

    // Fetch the tracking data again to ensure up-to-date information
     fetch(window.endpoints.rastreio + `?chave=${chave}`)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Erro ao buscar dados para o PDF");
        }
        return response.json();
      })
      .then((trackingData) => {
        if (trackingData) {
          const pdfContent = generatePDFContent(trackingData);

          const opt = {
            margin: [10, 10, 10, 10],
            filename: `rastreamento-Skymsen-${trackingCode}.pdf`,
            image: { type: "jpeg", quality: 0.98 },
            html2canvas: {
              scale: 2,
              useCORS: true,
              logging: false,
              removeContainer: true,
            },
            jsPDF: {
              unit: "mm",
              format: "a4",
              orientation: "portrait",
              compress: true,
            },
            pagebreak: { mode: "avoid-all" },
          };
          html2pdf().from(pdfContent).set(opt).save();
        } else {
          alert(
            "Não foi possível gerar o PDF pois os dados de rastreamento não foram encontrados."
          );
        }
      })
      .catch((error) => {
        console.error("Erro ao gerar PDF:", error);
        alert("Houve um erro ao gerar o PDF. Por favor, tente novamente.");
      });
  });

  // Filtro de eventos
  filterEvents.addEventListener("change", function () {
      const filter = this.value;
      const items = historyContainer.querySelectorAll(".timeline-item");
  
      items.forEach((item) => {
        const content = item.querySelector(".timeline-content");
        if (filter === "todos") {
          item.style.display = "flex";
        } else if (content && content.classList.contains(filter)) {
          item.style.display = "flex";
        } else {
          item.style.display = "none";
        }
      });
    });

  // Busca os dados dinamicamente através da API
   fetch(window.endpoints.rastreio + `?chave=${chave}`)
    .then((response) => {
      if (!response.ok) {
        throw new Error("Erro na requisição");
      }
      return response.json();
    })
    .then((trackingData) => {
      // Remove skeleton loader
      const skeletonLoader = document.querySelector(".skeleton-loader");
      if (skeletonLoader) {
        skeletonLoader.remove();
      }

      if (trackingData && trackingData.NUM_NF) {
        trackingCodeElement.textContent = trackingData.NUM_NF;
      } else if (chave) {
        trackingCodeElement.textContent = chave;
      } else {
        trackingCodeElement.textContent = "N/A";
      }

      console.log("Dados de rastreamento recebidos:", trackingData);

      if (trackingData) {
        remessaInfoCard.style.display = "block";

        // Atualiza o status principal dinamicamente
        remessaStatus.className = "status";
        if (trackingData.status_class && trackingData.status_class.trim()) {
          remessaStatus.classList.add(trackingData.status_class.trim());
        }
        remessaStatus.textContent =
          trackingData.status_description ||
          "Em processamento";

        // Atualiza a barra de progresso
        updateProgressBar(trackingData);

        if (trackingData.destinatario) {
          destinatarioInfo.style.display = "block";
          destinatarioSpan.textContent = trackingData.destinatario;
        }
        if (trackingData.remetente) {
          remetenteInfo.style.display = "block";
          remetenteSpan.textContent = trackingData.remetente;
        }
        if (trackingData.peso) {
          pesoInfo.style.display = "block";
          pesoBrtSpan.textContent =
            parseFloat(trackingData.peso).toFixed(2) + " kg";
        }
        if (trackingData.volumes) {
          volumesInfo.style.display = "block";
          volumesSpan.textContent = trackingData.volumes;
        }
        if (trackingData.data_postagem) {
          dataPostagemInfo.style.display = "block";
          dataPostagemSpan.textContent = formatDate(trackingData.data_postagem);
        }
        if (trackingData.previsao_entrega) {
          previsaoEntregaInfo.style.display = "block";
          previsaoEntregaSpan.textContent = formatDate(
            trackingData.previsao_entrega
          );
        }
        if (trackingData.tipo_servico) {
          tipoServicoInfo.style.display = "block";
          tipoServicoSpan.textContent = trackingData.tipo_servico;
        }
        if (trackingData.modalidade) {
          modalidadeInfo.style.display = "block";
          modalidadeSpan.textContent = trackingData.modalidade;
        }

        if (
          trackingData.campos_adicionais &&
          trackingData.campos_adicionais.length > 0
        ) {
          trackingData.campos_adicionais.forEach((campo) => {
            const infoItem = document.createElement("div");
            infoItem.classList.add("info-item");
            const strong = document.createElement("strong");
            strong.innerHTML = `<i class="fas fa-tag"></i> ${campo.nome}`;
            const span = document.createElement("span");
            span.textContent = campo.valor;
            infoItem.appendChild(strong);
            infoItem.appendChild(span);
            camposAdicionaisContainer.appendChild(infoItem);
          });
        }

        if (
          trackingData.historico_rastreamento &&
          trackingData.historico_rastreamento.length > 0
        ) {
          // Ordena eventos do mais recente para o mais antigo
          trackingData.historico_rastreamento.sort((a, b) => {
            return new Date(b.data_hora) - new Date(a.data_hora);
          });

          trackingData.historico_rastreamento.forEach((evento, index) => {
            const timelineItem = document.createElement("div");
            timelineItem.classList.add("timeline-item");

            if (index === 0) {
              timelineItem.classList.add("latest");
            }

            const timelineDate = document.createElement("div");
            timelineDate.classList.add("timeline-date");
            const dateTime = new Date(evento.data_hora);
            const formattedDate = formatDate(evento.data_hora);
            const formattedTime = dateTime.toLocaleTimeString("pt-BR");
            timelineDate.innerHTML = `
                                        
                                                <span class="formatted-date">${formattedDate}</span>
                                                        <span class="formatted-time">${formattedTime}</span>
                          
                                                      <span class="date-ago">${timeAgo(
                                                          dateTime
                                                      )}</span>
                                                    `;
            const timelineIndicator = document.createElement("div");
            timelineIndicator.classList.add("timeline-indicator");

            // Determina a classe dinâmica para o evento
            let eventClass = determineEventClass(evento);
            if (eventClass) {
              timelineIndicator.classList.add(eventClass);
            }

            // Adiciona ícone baseado no tipo de evento
            const icon = getEventIcon(eventClass);
            timelineIndicator.innerHTML = `<i class="${icon}"></i>`;

            const timelineContent = document.createElement("div");
            timelineContent.classList.add("timeline-content");
            if (eventClass) {
              timelineContent.classList.add(eventClass);
            }

            // Conteúdo do evento
            let eventDetailsHTML = "";
            if (evento.cidade_ocorrencia) {
              eventDetailsHTML += `
                                                            <div class="event-detail location">
                    
                                                      <i class="fas fa-map-marker-alt"></i>
                                                      <strong>Local:</strong> ${
                                                                  evento.cidade_ocorrencia
                                                      }${
                evento.uf ?
                ` - ${evento.uf}` : ""
              }
                                                            </div>`;
            }

            if (evento.filial) {
              eventDetailsHTML += `
                                                            <div class="event-detail">
                                                        <i class="fas fa-building"></i>
                                                      <strong>Filial:</strong> ${evento.filial}
                                                            </div>`;
            }

            if (evento.nome_recebedor) {
              eventDetailsHTML += `
                                                            <div class="event-detail recipient">
                                                         <i class="fas fa-user-check"></i>
                                                      <strong>Recebedor:</strong> ${
                                                                  evento.nome_recebedor
                                                      }
                                                      ${
                                                                  evento.documento_recebedor
                                                        ?
                                                        `(${evento.documento_recebedor})`
                                                                    : ""
                                                      }
                                                            </div>`;
            }

            if (evento.dominio) {
              eventDetailsHTML += `
                                                            <div class="event-detail">
                                                        <i class="fas fa-sitemap"></i>
                                                      <strong>Domínio:</strong> ${evento.dominio}
                                                            </div>`;
            }

            if (evento.codigo_ocorrencia) {
              eventDetailsHTML += `
                                                            <div class="event-detail code">
                                                         <i class="fas fa-hashtag"></i>
                                                      <strong>Código:</strong> ${evento.codigo_ocorrencia}
                                                            </div>`;
            }

            timelineContent.innerHTML = `
                                                            <h3>
                                                        ${
                                                              
                                                            evento.descricao_completa ||
                                                                evento.descricao_ocorrencia
                                                              }
                                                      <span class="tag tracking">${
                                                            
                                                          evento.descricao_ocorrencia ||
                                                            ""
                                                          }</span>
                                                        </h3>
                                                            <div class="event-details">
                                                              ${eventDetailsHTML}
                                                        </div>
                                                        `;
            // Adiciona quaisquer ações ou informações adicionais
            if (index === 0 && trackingData.status_class === "entregue") {
              const actionDiv = document.createElement("div");
              actionDiv.classList.add("timeline-actions");
              actionDiv.innerHTML = `
                                                                <button class="action-button">
                                                                    <i class="fas fa-file-signature"></i> Ver comprovante
                                                            </button>
                                                            `;
              timelineContent.appendChild(actionDiv);
            }

            timelineItem.appendChild(timelineDate);
            timelineItem.appendChild(timelineIndicator);
            timelineItem.appendChild(timelineContent);
            historyContainer.appendChild(timelineItem);
          });
          // Destaca o primeiro item (mais recente)
          const firstItem = historyContainer.firstElementChild;
          if (firstItem && firstItem.classList.contains("timeline-item")) {
            const indicator = firstItem.querySelector(".timeline-indicator");
            if (indicator) {
              indicator.classList.add("active");
            }
          }
        } else {
          const noEventsMessage = document.createElement("div");
          noEventsMessage.classList.add("no-events");
          noEventsMessage.innerHTML = `
                                                        <i class="fas fa-exclamation-circle"></i>
                                                        <p>Nenhum evento de rastreamento encontrado para esta encomenda.</p>
                                                        <button class="refresh-button">
                                                          <i class="fas fa-sync-alt"></i> Atualizar dados
                                                        </button>
                                                    `;
          historyContainer.appendChild(noEventsMessage);
        }

        currentYearSpan.textContent = new Date().getFullYear();

        const dataAtualizacaoElement = document.getElementById("data-atualizacao");
        const ultimaAtualizacaoBackend = trackingData.ultima_atualizacao;

        if (ultimaAtualizacaoBackend) {
          try {
            // Converter a string de data do MySQL para objeto Date
            // Formato esperado: "2025-04-04 16:42:12"
            const [datePart, timePart] = ultimaAtualizacaoBackend.split(' ');
            const [year, month, day] = datePart.split('-');
            const [hours, minutes, seconds] = timePart.split(':');
            
            // Criar objeto Date (meses são 0-indexados no JavaScript)
            const dataHora = new Date(year, month - 1, day, hours, minutes, seconds);
            
            // Verificar se a data é válida
            if (!isNaN(dataHora.getTime())) {
              const dataFormatada = dataHora.toLocaleDateString('pt-BR', {
                year: 'numeric',
                month: '2-digit',
                day: '2-digit',
              });
              const horaFormatada = dataHora.toLocaleTimeString('pt-BR', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
              });
              dataAtualizacaoElement.textContent = `Atualizado em: ${dataFormatada} às ${horaFormatada}`;
            } else {
              dataAtualizacaoElement.textContent = "Data de atualização inválida";
            }
          } catch (e) {
            console.error("Erro ao formatar data de atualização:", e);
            dataAtualizacaoElement.textContent = "Data de atualização não disponível";
          }
        } else {
          dataAtualizacaoElement.textContent = "Data de atualização não disponível";
        }
      }
    })
    .catch((error) => {
      console.error("Erro ao buscar dados:", error);
      historyContainer.innerHTML = `
                                                <div class="error-message">
                                                      <i class="fas fa-exclamation-triangle"></i>
                                                    <h3>Não foi possível carregar os dados de rastreamento</h3>
                                                    <p>Verifique se o código está correto ou tente novamente mais tarde.</p>
                                                    <button class="refresh-button" onclick="window.location.reload()">
                                                        <i class="fas fa-sync-alt"></i> Tentar novamente
                                                    </button>
                                                </div>
                                          `;
    });

  // Funções auxiliares
  function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString("pt-BR", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
  }

  function timeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);
    let interval = Math.floor(seconds / 31536000);
    if (interval > 1) return interval + " anos";
    interval = Math.floor(seconds / 2592000);
    if (interval > 1) return interval + " meses";
    interval = Math.floor(seconds / 86400);
    if (interval > 1) return interval + " dias";
    interval = Math.floor(seconds / 3600);
    if (interval > 1) return interval + " horas";
    interval = Math.floor(seconds / 60);
    if (interval > 1) return interval + " minutos";
    return Math.floor(seconds) + " segundos";
  }

  function determineEventClass(evento) {
      // Verifica primeiro a descrição completa ou descrição da ocorrência
      let descricao = (evento.descricao_completa || evento.descricao_ocorrencia || "").toLowerCase();
      
      // Em seguida, verifica o campo status se disponível
      let status = (evento.status || "").toLowerCase();
      
      // Unifica padrões de detecção para os diferentes status
      if (descricao.includes('entregue') || descricao.includes('concluído') || descricao.includes('delivered') ||
          status.includes('entregue') || status.includes('concluído') || status.includes('delivered')) {
          return 'entregue';
      }
      
      if (descricao.includes('saiu para entrega') || descricao.includes('out for delivery') ||
          descricao.includes('saida para entrega') || // Variação encontrada no updateProgressBar
          status.includes('saiu para entrega') || status.includes('out for delivery')) {
          return 'saiu-para-entrega'; // Padronizado com hífen
      }
      
      if (descricao.includes('em transito') || descricao.includes('em trânsito') || descricao.includes('transit') ||
          status.includes('transito') || status.includes('trânsito') || status.includes('transit')) {
          return 'em-transito'; // Padronizado com hífen
      }
      
      if (descricao.includes('coletado') || descricao.includes('collected') ||
          status.includes('coletado') || status.includes('collected')) {
          return 'coletado';
      }
      
      if (descricao.includes('postado') || descricao.includes('posted') ||
          status.includes('postado') || status.includes('posted')) {
          return 'postado';
      }
      
      if (descricao.includes('problema') || descricao.includes('problem') ||
          status.includes('problema') || status.includes('problem')) {
          return 'problema';
      }
      
      // Verificações adicionais para status específicos do sistema
      if (descricao.includes('indisponível') || status.includes('indisponivel')) {
          return 'indisponivel';
      }
      
      return 'desconhecido'; // Status padrão para casos não identificados
  }

  // FUNÇÃO CORRIGIDA: Ícones alinhados com as classificações de status
  function getEventIcon(eventClass) {
      switch (eventClass) {
          case "entregue":
              return "fas fa-check-circle"; // Ícone de entregue
          case "saiu-para-entrega":
              return "fas fa-truck"; // Ícone de caminhão para entrega
          case "em-transito":
          case "transito": // Para compatibilidade com possíveis classes antigas
              return "fas fa-shipping-fast"; // Ícone de transporte
          case "coletado":
              return "fas fa-box"; // Ícone de pacote coletado
          case "postado":
              return "fas fa-mail-bulk"; // Ícone de postagem
          case "problema":
              return "fas fa-exclamation-triangle"; // Ícone de alerta
          case "indisponivel":
              return "fas fa-question-circle"; // Ícone de indisponível
          default:
              return "fas fa-info-circle"; // Ícone padrão para outros casos
      }
  }

  // FUNÇÃO CORRIGIDA: Atualização da barra de progresso alinhada com as classificações
  function updateProgressBar(trackingData) {
      // Definição dos valores de progressão de cada etapa
      const steps = {
          "postado": 1,
          "coletado": 2,
          "em-transito": 3,
          "transito": 3, // Para compatibilidade
          "saiu-para-entrega": 4,
          "entregue": 5,
          "problema": 2.5, // Mantido como etapa intermediária
          "indisponivel": 0,
          "desconhecido": 0
      };
      
      let currentStatus = "desconhecido";
      
      // Priorize a verificação do último evento
      if (trackingData.historico_rastreamento && trackingData.historico_rastreamento.length > 0) {
          const lastEvent = trackingData.historico_rastreamento[0];
          const descricao = (lastEvent.descricao_completa || lastEvent.descricao_ocorrencia || "").toUpperCase();
          
          // Determina o status com base no último evento usando a mesma lógica de determineEventClass
          currentStatus = determineEventClass(lastEvent);
          
          // Correção para casos especiais verificados diretamente nas descrições
          if (descricao.includes("SAIDA PARA ENTREGA") || descricao.includes("SAIU PARA ENTREGA")) {
              currentStatus = "saiu-para-entrega";
          } else if (descricao.includes("ENTREGUE")) {
              currentStatus = "entregue";
          }
      } else {
          // Se não houver eventos, use o status_class do objeto principal
          currentStatus = trackingData.status_class || "desconhecido";
      }
      
      // Obtém o valor numérico da etapa atual
      const currentStep = steps[currentStatus] || 0;
      
      // Calcula a porcentagem de progresso
      const totalSteps = 5; // Total de etapas do rastreamento (excluindo problema/indisponível)
      const progressPercentage = (currentStep / totalSteps) * 100;
      
      // Atualiza o indicador de progresso
      if (progressIndicator) {
          progressIndicator.style.width = `${Math.min(progressPercentage, 100)}%`;
      }
      
      // Atualiza os passos do progresso
      const progressSteps = document.querySelectorAll(".progress-step");
      progressSteps.forEach((step) => {
          const stepData = step.getAttribute("data-step");
          const stepValue = steps[stepData] || 0;
          
          if (stepValue > 0 && stepValue < currentStep) {
              step.classList.add("completed");
              step.classList.remove("current");
          } else if (stepValue === currentStep && currentStep > 0) {
              step.classList.add("current");
              step.classList.remove("completed");
          } else {
              step.classList.remove("completed");
              step.classList.remove("current");
          }
      });
      
      // Lógica adicional para status 'indisponivel' e 'desconhecido'
      if (currentStatus === "indisponivel" || currentStatus === "desconhecido") {
          if (progressIndicator) {
              progressIndicator.style.width = "0%";
          }
          progressSteps.forEach((step) => {
              step.classList.remove("completed", "current");
          });
      }
  }

  // Function to generate well-formatted PDF content
  function generatePDFContent(trackingData) {
    const trackingCode = trackingData.NUM_NF ||
      "N/A";
    const currentDate = new Date().toLocaleString("pt-BR");

    // Create the base container with PDF styling
    const pdfContainer = document.createElement("div");
    pdfContainer.className = "pdf-container";
    pdfContainer.style.padding = "15px";
    pdfContainer.style.backgroundColor = "#ffffff";
    pdfContainer.style.fontFamily = "Arial, sans-serif";
    // Add PDF header
    const header = document.createElement("div");
    header.className = "pdf-header";
    header.style.textAlign = "center";
    header.style.marginBottom = "20px";
    header.style.borderBottom = "2px solid #eaeaea";
    header.style.paddingBottom = "15px";
    header.innerHTML = `
            <div style="display: flex; align-items: center; justify-content: center; margin-bottom: 10px;">
                <div style="font-size: 24px; font-weight: bold; color: #333;">
                    <i class="fas fa-truck-fast"></i>
                    Logis<span style="color: #0056b3;">Track</span>
                </div>
            </div>
            <div style="font-size: 18px; color: #555;">Comprovante de Rastreamento</div>
        `;
    pdfContainer.appendChild(header);

    // Add info card content
    const infoCard = document.createElement("div");
    infoCard.className = "info-card";
    infoCard.style.marginBottom = "20px";
    infoCard.style.padding = "15px";
    infoCard.style.border = "1px solid #ddd";
    infoCard.style.borderRadius = "5px";
    infoCard.style.pageBreakInside = "avoid";
    infoCard.style.breakInside = "avoid";
    let infoHTML = "";
    if (trackingCode)
      infoHTML += `<p><strong>Código de Rastreamento:</strong> ${trackingCode}</p>`;
    if (trackingData.status_description)
      infoHTML += `<p><strong>Status:</strong> ${trackingData.status_description}</p>`;
    if (trackingData.destinatario)
      infoHTML += `<p><strong>Destinatário:</strong> ${trackingData.destinatario}</p>`;
    if (trackingData.remetente)
      infoHTML += `<p><strong>Remetente:</strong> ${trackingData.remetente}</p>`;
    if (trackingData.peso)
      infoHTML += `<p><strong>Peso:</strong> ${parseFloat(
        trackingData.peso
      ).toFixed(2)} kg</p>`;
    if (trackingData.volumes)
      infoHTML += `<p><strong>Volumes:</strong> ${trackingData.volumes}</p>`;
    if (trackingData.data_postagem)
      infoHTML += `<p><strong>Data de Postagem:</strong> ${formatDate(
        trackingData.data_postagem
      )}</p>`;
    if (trackingData.previsao_entrega)
      infoHTML += `<p><strong>Previsão de Entrega:</strong> ${formatDate(
        trackingData.previsao_entrega
      )}</p>`;
    if (trackingData.tipo_servico)
      infoHTML += `<p><strong>Tipo de Serviço:</strong> ${trackingData.tipo_servico}</p>`;
    if (trackingData.modalidade)
      infoHTML += `<p><strong>Modalidade:</strong> ${trackingData.modalidade}</p>`;
    if (
      trackingData.campos_adicionais &&
      trackingData.campos_adicionais.length > 0
    ) {
      trackingData.campos_adicionais.forEach((campo) => {
        infoHTML += `<p><strong>${campo.nome}:</strong> ${campo.valor}</p>`;
      });
    }

    infoCard.innerHTML = infoHTML;
    pdfContainer.appendChild(infoCard);

    // Add tracking history
    if (
      trackingData.historico_rastreamento &&
      trackingData.historico_rastreamento.length > 0
    ) {
      const historyTitle = document.createElement("h2");
      historyTitle.textContent = "Histórico de Rastreamento";
      historyTitle.style.fontSize = "1.2em";
      historyTitle.style.marginBottom = "10px";
      pdfContainer.appendChild(historyTitle);

      const timelineItems = document.createElement("div");
      timelineItems.className = "timeline-items-pdf";
      trackingData.historico_rastreamento.forEach((evento) => {
        const item = document.createElement("div");
        item.className = "timeline-item";
        item.style.display = "block";
        item.style.pageBreakInside = "avoid";
        item.style.breakInside = "avoid";
        item.style.marginBottom = "15px";
        item.style.padding = "10px";
        item.style.border = "1px solid #eaeaea";
        item.style.borderRadius = "5px";

        const date = document.createElement("div");
        date.style.fontSize = "0.9em";
        date.style.color = "#555";
        const dateTime = new Date(evento.data_hora);
        date.textContent = `${formatDate(
          evento.data_hora
        )} - ${dateTime.toLocaleTimeString("pt-BR")}`;
        item.appendChild(date);

        const description = document.createElement("div");
        description.style.marginTop = "5px";
        description.innerHTML = `<strong>${
          evento.descricao_completa || evento.descricao_ocorrencia
        }</strong>`;
        if (evento.cidade_ocorrencia) {
          description.innerHTML += `<br>Local: ${evento.cidade_ocorrencia}${
            evento.uf ?
            ` - ${evento.uf}` : ""
          }`;
        }
        if (evento.filial) {
          description.innerHTML += `<br>Filial: ${evento.filial}`;
        }
        if (evento.nome_recebedor) {
          description.innerHTML += `<br>Recebedor: ${evento.nome_recebedor} ${
            evento.documento_recebedor ?
            `(${evento.documento_recebedor})` : ""
          }`;
        }
        if (evento.dominio) {
          description.innerHTML += `<br>Domínio: ${evento.dominio}`;
        }
        if (evento.codigo_ocorrencia) {
          description.innerHTML += `<br>Código: ${evento.codigo_ocorrencia}`;
        }
        item.appendChild(description);
        timelineItems.appendChild(item);
      });
      pdfContainer.appendChild(timelineItems);
    } else {
      const noEvents = document.createElement("p");
      noEvents.textContent = "Nenhum evento de rastreamento encontrado.";
      pdfContainer.appendChild(noEvents);
    }

    // Add PDF footer
    const footer = document.createElement("div");
    footer.style.marginTop = "20px";
    footer.style.borderTop = "1px solid #eaeaea";
    footer.style.paddingTop = "10px";
    footer.style.fontSize = "10px";
    footer.style.color = "#777";
    footer.style.textAlign = "center";
    footer.innerHTML = `
            <div>Documento gerado em: ${currentDate}</div>
            <div>Skymsen - Sistema de Rastreamento de Cargas</div>
        `;
    pdfContainer.appendChild(footer);

    return pdfContainer;
  }
  
});