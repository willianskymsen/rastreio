document.addEventListener("DOMContentLoaded", function () {
  // Elementos da interface
  const pendentesCardBody = document.querySelector("#ocorrenciasPendentesCard .card-body");
  const togglePendentesBtn = document.getElementById("togglePendentesBtn");
  const pendingCountBadge = document.getElementById("pending-count-badge");
  const totalCountBadge = document.getElementById("totalCountBadge");
  const refreshBtn = document.getElementById("refreshBtn");
  const exportBtn = document.getElementById("exportBtn");
  const searchInput = document.getElementById("searchInput");
  const reloadBtn = document.getElementById("reloadBtn");
  const reloadPendentesBtn = document.getElementById("reloadPendentesBtn");
  const ocorrenciasTableBody = document.querySelector("#ocorrenciasTable tbody");
  const noOcorrenciasRow = document.getElementById("no-ocorrencias-row");
  const loadingRow = document.getElementById("loading-row");
  const loadOcorrenciasErrorRow = document.getElementById("load-ocorrencias-error-row");
  const paginationContainer = document.getElementById("pagination");

  // Cache para armazenar dados de ocorrências
  let ocorrenciasData = [];
  let ocorrenciasPendentesData = [];

  // Configurações de paginação
  const itemsPerPage = 10;
  let currentPage = 1;
  let filteredData = [];

  // 1. Implementação para o card-body (expansível/recolhível)
  function setupCardBody() {
      if (pendentesCardBody) {
          // Adicionar classe collapse do Bootstrap para controle via JavaScript
          pendentesCardBody.classList.add("collapse", "show");
      }
  }

  // 2. Implementação para o botão toggle
  function setupTogglePendentesBtn() {
      if (togglePendentesBtn && pendentesCardBody) {
          togglePendentesBtn.addEventListener("click", function () {
              // Toggle usando o collapse do Bootstrap
              const collapse = bootstrap.Collapse.getOrCreateInstance(pendentesCardBody);
              if (pendentesCardBody.classList.contains("show")) {
                  collapse.hide();
                  togglePendentesBtn.querySelector("i").classList.remove("bi-chevron-up");
                  togglePendentesBtn.querySelector("i").classList.add("bi-chevron-down");
                  togglePendentesBtn.setAttribute("aria-expanded", "false");
              } else {
                  collapse.show();
                  togglePendentesBtn.querySelector("i").classList.remove("bi-chevron-down");
                  togglePendentesBtn.querySelector("i").classList.add("bi-chevron-up");
                  togglePendentesBtn.setAttribute("aria-expanded", "true");
              }
          });
      }
  }

  // 3. Implementação para o pendingCountBadge
  function updatePendingCountBadge(count) {
      if (pendingCountBadge) {
          pendingCountBadge.textContent = count;

          // Atualizar a cor do badge baseado na contagem
          pendingCountBadge.classList.remove("bg-warning", "bg-success", "bg-danger");

          if (count === 0) {
              pendingCountBadge.classList.add("bg-success");
          } else if (count > 0) {
              pendingCountBadge.classList.add("bg-warning");
          } else {
              // Para casos de erro (?, !)
              pendingCountBadge.classList.add("bg-danger");
          }
      }
  }

  // 4. Implementação para o totalCountBadge
  function updateTotalCountBadge(count) {
      if (totalCountBadge) {
          totalCountBadge.textContent = count;

          // Atualizar a cor do badge baseado na contagem
          totalCountBadge.classList.remove("bg-primary", "bg-danger");

          if (isNaN(count) || count === "?" || count === "!") {
              totalCountBadge.classList.add("bg-danger");
          } else {
              totalCountBadge.classList.add("bg-primary");
          }
      }
  }

  // 5. Implementação para o refreshBtn
  function setupRefreshBtn() {
      if (refreshBtn) {
          refreshBtn.addEventListener("click", function () {
              // Adicionar efeito de rotação ao ícone durante o carregamento
              const icon = refreshBtn.querySelector("i");
              refreshBtn.disabled = true;
              icon.classList.add("rotate-animation");

              // Recarregar dados
              Promise.all([
                  loadOcorrencias(),
                  loadOcorrenciasPendentes()
              ]).then(() => {
                  // Mostrar toast de sucesso
                  showToast("Dados atualizados com sucesso!", false);
              }).catch(error => {
                  showToast("Erro ao atualizar dados.", true);
                  console.error("Erro ao atualizar dados:", error);
              }).finally(() => {
                  // Remover efeito de rotação e reativar botão
                  setTimeout(() => {
                      icon.classList.remove("rotate-animation");
                      refreshBtn.disabled = false;
                  }, 500);
              });
          });
      }
  }

  // 6. Implementação para o exportBtn
  function setupExportBtn() {
      if (exportBtn) {
          exportBtn.addEventListener("click", function () {
              if (ocorrenciasData.length === 0) {
                  showToast("Não há dados para exportar.", true);
                  return;
              }

              // Determinar se exportamos dados filtrados ou todos
              const dataToExport = filteredData.length > 0 ? filteredData : ocorrenciasData;

              try {
                  // Criar workbook e worksheet
                  const wb = XLSX.utils.book_new();

                  // Preparar dados para exportação (incluir Código Interno)
                  const exportData = dataToExport.map(item => ({
                      "Código SSW": item.CODIGO_SSW,
                      "Código Interno": item.COD_INTERNO || '',
                      "Descrição": item.DESCRICAO,
                      "Data Cadastro": new Date().toLocaleDateString('pt-BR')
                  }));

                  const ws = XLSX.utils.json_to_sheet(exportData);

                  // Adicionar a worksheet ao workbook
                  XLSX.utils.book_append_sheet(wb, ws, "Ocorrências");

                  // Gerar arquivo Excel e realizar download
                  const now = new Date();
                  const dateStr = `${now.getDate()}-${now.getMonth() + 1}-${now.getFullYear()}`;
                  XLSX.writeFile(wb, `ocorrencias_${dateStr}.xlsx`);

                  showToast(`${exportData.length} ocorrências exportadas com sucesso!`, false);
              } catch (error) {
                  console.error("Erro ao exportar dados:", error);
                  showToast("Erro ao exportar dados.", true);
              }
          });
      }
  }

  // Função para mostrar mensagens toast melhorada
  function showToast(message, isError = false) {
      const toastElement = document.getElementById('toast-template');
      if (toastElement) {
          const toastMessageElement = toastElement.querySelector('#toastMessage');
          if (toastMessageElement) {
              toastMessageElement.textContent = message;
          }

          if (isError) {
              toastElement.classList.remove('bg-success');
              toastElement.classList.add('bg-danger');
          } else {
              toastElement.classList.remove('bg-danger');
              toastElement.classList.add('bg-success');
          }

          const toastBootstrap = bootstrap.Toast.getOrCreateInstance(toastElement);
          toastBootstrap.show();
      } else {
          console.error("Elemento toast com ID 'toast-template' não encontrado.");
      }
  }

  // Função para carregar as ocorrências melhorada
  function loadOcorrencias() {
      return new Promise((resolve, reject) => {
          if (
              typeof STATUS_CONFIG !== "undefined" &&
              STATUS_CONFIG.urls &&
              STATUS_CONFIG.urls.getOcorrencias
          ) {
              const url = STATUS_CONFIG.urls.getOcorrencias;

              // Mostrar indicador de carregamento
              if (loadingRow) loadingRow.style.display = "";
              if (loadOcorrenciasErrorRow) loadOcorrenciasErrorRow.style.display = "none";
              if (noOcorrenciasRow) noOcorrenciasRow.style.display = "none";

              fetch(url)
                  .then((response) => {
                      if (!response.ok) {
                          throw new Error(`Erro na requisição: ${response.status}`);
                      }
                      return response.json();
                  })
                  .then((data) => {
                      // Armazenar dados no cache
                      ocorrenciasData = data;

                      // Esconder indicador de carregamento
                      if (loadingRow) loadingRow.style.display = "none";

                      // Limpar tabela
                      ocorrenciasTableBody.innerHTML = "";

                      if (data && data.length > 0) {
                          // Atualizar contador
                          updateTotalCountBadge(data.length);

                          // Aplicar filtragem (para manter filtros atuais)
                          applyFilters();

                          // Resolver a promise
                          resolve(data);
                      } else {
                          if (noOcorrenciasRow) noOcorrenciasRow.style.display = "";
                          updateTotalCountBadge("0");
                          resolve([]);
                      }
                  })
                  .catch((error) => {
                      console.error("Erro ao buscar ocorrências:", error);
                      // Mostrar mensagem de erro
                      if (loadingRow) loadingRow.style.display = "none";
                      if (loadOcorrenciasErrorRow) loadOcorrenciasErrorRow.style.display = "";
                      updateTotalCountBadge("?");
                      reject(error);
                  });
          } else {
              console.error("A configuração STATUS_CONFIG ou a URL para buscar ocorrências não foram definidas.");
              if (loadOcorrenciasErrorRow) {
                  loadOcorrenciasErrorRow.querySelector("td").textContent = "Erro de configuração.";
                  loadOcorrenciasErrorRow.style.display = "";
              }
              updateTotalCountBadge("!");
              reject(new Error("Configuração inválida"));
          }
      });
  }

  // Função para carregar ocorrências pendentes melhorada
  function loadOcorrenciasPendentes() {
      return new Promise((resolve, reject) => {
          if (
              typeof STATUS_CONFIG !== "undefined" &&
              STATUS_CONFIG.urls &&
              STATUS_CONFIG.urls.getOcorrenciasPendentes
          ) {
              const url = STATUS_CONFIG.urls.getOcorrenciasPendentes;
              const ocorrenciasPendentesTableBody = document.querySelector("#ocorrenciasPendentesTable tbody");
              const loadingPendentesRow = document.getElementById("loading-pendentes-row");
              const loadingPendentesErrorRow = document.getElementById("loading-pendentes-error-row");
              const noOcorrenciasPendentes = document.getElementById("no-ocorrencias-pendentes");

              // Mostrar indicador de carregamento
              if (loadingPendentesRow) loadingPendentesRow.style.display = "";
              if (loadingPendentesErrorRow) loadingPendentesErrorRow.style.display = "none";
              if (noOcorrenciasPendentes) noOcorrenciasPendentes.style.display = "none";

              fetch(url)
                  .then((response) => {
                      if (!response.ok) {
                          throw new Error(`Erro na requisição: ${response.status}`);
                      }
                      return response.json();
                  })
                  .then((data) => {
                      // Armazenar dados no cache
                      ocorrenciasPendentesData = data;

                      // Esconder indicador de carregamento
                      if (loadingPendentesRow) loadingPendentesRow.style.display = "none";

                      // Atualizar o badge de contagem de pendentes
                      updatePendingCountBadge(data.length);

                      if (ocorrenciasPendentesTableBody) {
                          ocorrenciasPendentesTableBody.innerHTML = "";

                          // Adicionar linha de carregamento (escondida)
                          ocorrenciasPendentesTableBody.appendChild(loadingPendentesRow);

                          if (data && data.length > 0) {
                              data.forEach((ocorrencia) => {
                                  const row = document.createElement("tr");

                                  const descricaoCell = document.createElement("td");
                                  descricaoCell.textContent = ocorrencia.tipo_ocorrencia || "Sem descrição";
                                  row.appendChild(descricaoCell);

                                  const actionsCell = document.createElement("td");
                                  actionsCell.classList.add("text-center");

                                  const assignCodeButton = document.createElement("button");
                                  assignCodeButton.classList.add("btn", "btn-sm", "btn-outline-primary");
                                  assignCodeButton.textContent = "Atribuir Código";
                                  assignCodeButton.dataset.ocorrenciaId = ocorrencia.id;
                                  assignCodeButton.addEventListener("click", () => openAssignCodeModal(ocorrencia.id));

                                  actionsCell.appendChild(assignCodeButton);
                                  row.appendChild(actionsCell);

                                  ocorrenciasPendentesTableBody.appendChild(row);
                              });

                              if (noOcorrenciasPendentes) noOcorrenciasPendentes.style.display = "none";
                          } else {
                              if (noOcorrenciasPendentes) noOcorrenciasPendentes.style.display = "block";
                          }
                      }
                      resolve(data);
                  })
                  .catch((error) => {
                      console.error("Erro ao buscar ocorrências pendentes:", error);
                      if (loadingPendentesRow) loadingPendentesRow.style.display = "none";
                      if (loadingPendentesErrorRow) loadingPendentesErrorRow.style.display = "";
                      updatePendingCountBadge("?");
                      reject(error);
                  });
          } else {
              console.error("A configuração STATUS_CONFIG ou a URL para buscar ocorrências pendentes não foram definidas.");
              updatePendingCountBadge("!");
              reject(new Error("Configuração inválida"));
          }
      });
  }

  // Função para abrir modal de atribuir código
  function openAssignCodeModal(id) {
      const atribuirCodigoModal = document.getElementById("atribuirCodigoModal");
      const ocorrenciaPendenteIdInput = document.getElementById("ocorrenciaPendenteId");
      const novoCodigoInput = document.getElementById("novoCodigo");

      if (atribuirCodigoModal && ocorrenciaPendenteIdInput && novoCodigoInput) {
          // Buscar detalhes da ocorrência pendente pelo ID
          fetch(`${STATUS_CONFIG.urls.getOcorrenciasPendentes}/${id}`)
              .then((response) => response.json())
              .then((data) => {
                  // Preencher o formulário com os dados da ocorrência
                  ocorrenciaPendenteIdInput.value = id;
                  document.getElementById("atribuirCodigoDescricao").textContent =
                      data.tipo_ocorrencia || "Sem descrição";
                  document.getElementById("novoTipo").value =
                      data.tipo_ocorrencia || "";
                  novoCodigoInput.value = "";
                  const modal = new bootstrap.Modal(atribuirCodigoModal);
                  modal.show();
              })
              .catch((error) => {
                  console.error("Erro ao buscar detalhes da ocorrência pendente:", error);
                  showToast("Erro ao carregar detalhes da ocorrência", true);
              });
      } else {
          console.warn("Modal de atribuir código ou campos de entrada não encontrados.");
      }
  }

  // Função para aplicar filtros aos dados
  function applyFilters() {
      const searchText = searchInput ? searchInput.value.toLowerCase() : '';

      filteredData = ocorrenciasData.filter(item => {
          // Filtrar por texto de pesquisa (incluindo Código Interno)
          const matchesSearch = searchText === '' ||
              (item.CODIGO_SSW && item.CODIGO_SSW.toLowerCase().includes(searchText)) ||
              (item.COD_INTERNO && item.COD_INTERNO.toLowerCase().includes(searchText)) ||
              (item.DESCRICAO && item.DESCRICAO.toLowerCase().includes(searchText));

          return matchesSearch;
      });

      // Atualizar a exibição
      renderOcorrencias(filteredData);
      updatePagination(filteredData);
  }

  // Função para renderizar ocorrências na tabela
  function renderOcorrencias(data) {
      // Limpar tabela, mas preservar linhas especiais
      const rows = ocorrenciasTableBody.querySelectorAll('tr:not(#loading-row):not(#load-ocorrencias-error-row):not(#no-ocorrencias-row)');
      rows.forEach(row => row.remove());

      // Determinar quais ocorrências mostrar na página atual
      const start = (currentPage - 1) * itemsPerPage;
      const end = start + itemsPerPage;
      const pageItems = data.slice(start, end);

      if (pageItems.length > 0) {
          // Adicionar ocorrências à tabela
          pageItems.forEach((ocorrencia) => {
              const row = document.createElement("tr");
              row.dataset.codigoSsw = ocorrencia.CODIGO_SSW;

              // Criar células
              const codigoSSWCell = document.createElement("td");
              codigoSSWCell.textContent = ocorrencia.CODIGO_SSW;
              row.appendChild(codigoSSWCell);

              const codigoInternoCell = document.createElement("td");
              codigoInternoCell.textContent = ocorrencia.COD_INTERNO || '';
              row.appendChild(codigoInternoCell);

              const descricaoCell = document.createElement("td");
              descricaoCell.textContent = ocorrencia.DESCRICAO;
              row.appendChild(descricaoCell);

              const actionsCell = document.createElement("td");
              actionsCell.classList.add("text-center");

              // Botão editar
              const editButton = document.createElement("button");
              editButton.classList.add("btn", "btn-sm", "btn-primary", "me-2");
              editButton.innerHTML = '<i class="bi bi-pencil"></i> Editar';
              editButton.addEventListener("click", () => openEditModal(ocorrencia));
              actionsCell.appendChild(editButton);

              // Botão excluir
              const deleteButton = document.createElement("button");
              deleteButton.classList.add("btn", "btn-sm", "btn-danger");
              deleteButton.innerHTML = '<i class="bi bi-trash"></i> Excluir';
              deleteButton.addEventListener("click", () => inativarOcorrencia(ocorrencia.CODIGO_SSW, row));
              actionsCell.appendChild(deleteButton);

              row.appendChild(actionsCell);
              ocorrenciasTableBody.appendChild(row);
          });

          if (noOcorrenciasRow) noOcorrenciasRow.style.display = "none";
      } else {
          if (data.length === 0) {
              if (noOcorrenciasRow) noOcorrenciasRow.style.display = "";
          } else {
              // Não há resultados para os filtros atuais
              const noResultsRow = document.createElement("tr");
              const cell = document.createElement("td");
              cell.colSpan = 4; // Ajustar o colSpan para o novo número de colunas
              cell.classList.add("text-center", "text-muted", "py-4");
              cell.innerHTML = '<i class="bi bi-filter-circle me-2"></i>Nenhuma ocorrência corresponde aos filtros aplicados.';
              noResultsRow.appendChild(cell);
              ocorrenciasTableBody.appendChild(noResultsRow);
          }
      }
  }

  // Função para atualizar a paginação
  function updatePagination(data) {
      if (!paginationContainer) return;

      paginationContainer.innerHTML = '';

      const totalPages = Math.ceil(data.length / itemsPerPage);

      if (totalPages <= 1) return;

      // Botão Anterior
      const prevLi = document.createElement('li');
      prevLi.classList.add('page-item');
      if (currentPage === 1) prevLi.classList.add('disabled');

      const prevBtn = document.createElement('a');
      prevBtn.classList.add('page-link');
      prevBtn.href = '#';
      prevBtn.innerHTML = '&laquo;';
      prevBtn.addEventListener('click', (e) => {
          e.preventDefault();
          if (currentPage > 1) {
              currentPage--;
              renderOcorrencias(data);
              updatePagination(data);
          }
      });

      prevLi.appendChild(prevBtn);
      paginationContainer.appendChild(prevLi);

      // Determinar quais páginas mostrar
      let startPage = Math.max(1, currentPage - 2);
      let endPage = Math.min(totalPages, startPage + 4);

      if (endPage - startPage < 4) {
          startPage = Math.max(1, endPage - 4);
      }

      // Botões de páginas
      for (let i = startPage; i <= endPage; i++) {
          const pageLi = document.createElement('li');
          pageLi.classList.add('page-item');
          if (i === currentPage) pageLi.classList.add('active');

          const pageBtn = document.createElement('a');
          pageBtn.classList.add('page-link');
          pageBtn.href = '#';
          pageBtn.textContent = i;
          pageBtn.addEventListener('click', (e) => {
              e.preventDefault();
              currentPage = i;
              renderOcorrencias(data);
              updatePagination(data);
          });

          pageLi.appendChild(pageBtn);
          paginationContainer.appendChild(pageLi);
      }

      // Botão Próximo
      const nextLi = document.createElement('li');
      nextLi.classList.add('page-item');
      if (currentPage === totalPages) nextLi.classList.add('disabled');

      const nextBtn = document.createElement('a');
      nextBtn.classList.add('page-link');
      nextBtn.href = '#';
      nextBtn.innerHTML = '&raquo;';
      nextBtn.addEventListener('click', (e) => {
          e.preventDefault();
          if (currentPage < totalPages) {
              currentPage++;
              renderOcorrencias(data);
              updatePagination(data);
          }
      });

      nextLi.appendChild(nextBtn);
      paginationContainer.appendChild(nextLi);
  }

  // Configurar eventos de filtro
  function setupFilterEvents() {
      if (searchInput) {
          searchInput.addEventListener('input', () => {
              currentPage = 1; // Voltar para a primeira página ao filtrar
              applyFilters();
          });
      }
  }

  // Configurar botões de recarregar
  function setupReloadButtons() {
      if (reloadBtn) {
          reloadBtn.addEventListener('click', (e) => {
              e.preventDefault();
              loadOcorrencias();
          });
      }

      if (reloadPendentesBtn) {
          reloadPendentesBtn.addEventListener('click', (e) => {
              e.preventDefault();
              loadOcorrenciasPendentes();
          });
      }
  }

  // Adicionar função para abrir modal de edição
  function openEditModal(ocorrencia) {
      const editModal = document.getElementById('editarOcorrenciaModal');
      if (editModal) {
          document.getElementById('editCodigoSSW').value = ocorrencia.CODIGO_SSW;
          document.getElementById('editCodigoInterno').value = ocorrencia.COD_INTERNO || '';
          document.getElementById('editDescricao').value = ocorrencia.DESCRICAO;
          const modal = new bootstrap.Modal(editModal);
          modal.show();
      }
  }

  // Adicionar função de inativar ocorrência
  function inativarOcorrencia(codigoSSW, rowElement) {
      if (confirm("Tem certeza que deseja excluir esta ocorrência?")) {
          const url = `${STATUS_CONFIG.urls.inativarOcorrencia}/${codigoSSW}`;
          fetch(url, {
              method: "PUT",
          })
              .then((response) => {
                  if (!response.ok) {
                      return response.json().then((err) => {
                          throw new Error(err.error || "Erro ao excluir ocorrência.");
                      });
                  }
                  return response.json();
              })
              .then((data) => {
                  showToast("Ocorrência excluída com sucesso!");

                  // Remover do cache de dados
                  ocorrenciasData = ocorrenciasData.filter(item => item.CODIGO_SSW !== codigoSSW);

                  // Atualizar exibição
                  currentPage = 1;
                  applyFilters();

                  // Atualizar contadores
                  updateTotalCountBadge(ocorrenciasData.length);

                  // Recarregar pendentes
                  loadOcorrenciasPendentes();
              })
              .catch((error) => {
                  console.error("Erro ao excluir ocorrência:", error);
                  showToast(error.message, true);
              });
      }
  }

  // Adicionar animação CSS para ícones giratórios
  function addRotationStyles() {
      const style = document.createElement('style');
      style.innerHTML = `
          @keyframes rotate {
              from { transform: rotate(0deg); }
              to { transform: rotate(360deg); }
          }
          .rotate-animation {
              animation: rotate 1s linear infinite;
          }
      `;
      document.head.appendChild(style);
  }

  // Inicialização
  function init() {
      // Adicionar estilos para animações
      addRotationStyles();

      // Configurar elementos da interface
      setupCardBody();
      setupTogglePendentesBtn();
      setupRefreshBtn();
      setupExportBtn();
      setupFilterEvents();
      setupReloadButtons();

      // Carregar dados iniciais
      loadOcorrencias()
          .then(() => {
              console.log("Ocorrências carregadas com sucesso");
          })
          .catch(error => {
              console.error("Erro ao carregar ocorrências:", error);
          });

      loadOcorrenciasPendentes()
          .then(() => {
              console.log("Ocorrências pendentes carregadas com sucesso");
          })
          .catch(error => {
              console.error("Erro ao carregar ocorrências pendentes:", error);
          });

      // Configurar o modal de edição (exemplo básico - precisa da lógica para salvar)
      const editarOcorrenciaForm = document.getElementById('editarOcorrenciaForm');
      const salvarEditarBtn = document.getElementById('salvarEditarBtn');
      if (editarOcorrenciaForm && salvarEditarBtn) {
          salvarEditarBtn.addEventListener('click', function() {
              const codigoSSW = document.getElementById('editCodigoSSW').value;
              const codigoInterno = document.getElementById('editCodigoInterno').value;
              const descricao = document.getElementById('editDescricao').value;
              // Aqui você faria a chamada para a sua API para salvar as alterações
              console.log('Salvando edição:', codigoSSW, codigoInterno, descricao);
              // Após salvar, você pode fechar o modal e recarregar os dados
              const editModal = bootstrap.Modal.getInstance(document.getElementById('editarOcorrenciaModal'));
              editModal.hide();
              loadOcorrencias();
          });
      }

      // Configurar o modal de adicionar (exemplo básico - precisa da lógica para salvar)
      const adicionarOcorrenciaForm = document.getElementById('adicionarOcorrenciaForm');
      const salvarNovaOcorrenciaBtn = document.getElementById('salvarNovaOcorrenciaBtn');
      if (adicionarOcorrenciaForm && salvarNovaOcorrenciaBtn) {
          salvarNovaOcorrenciaBtn.addEventListener('click', function() {
              const codigoSSW = document.getElementById('codigo_ssw').value;
              const codigoInterno = document.getElementById('COD_INTERNO').value;
              const descricao = document.getElementById('descricao').value;
              // Aqui você faria a chamada para a sua API para adicionar a ocorrência
              console.log('Adicionando ocorrência:', codigoSSW, codigoInterno, descricao);
              // Após salvar, você pode fechar o modal e recarregar os dados
              const adicionarOcorrenciaModal = bootstrap.Modal.getInstance(document.getElementById('adicionarOcorrenciaModal'));
              adicionarOcorrenciaModal.hide();
              loadOcorrencias();
              loadOcorrenciasPendentes(); // Recarregar pendentes também, caso a nova ocorrência as afete
          });
      }

      // Configurar o modal de atribuir código (exemplo básico - precisa da lógica para salvar)
      const atribuirCodigoForm = document.getElementById('atribuirCodigoForm');
      const salvarNovoCodigoBtn = document.getElementById('salvarNovoCodigoBtn');
      if (atribuirCodigoForm && salvarNovoCodigoBtn) {
          salvarNovoCodigoBtn.addEventListener('click', function() {
              const ocorrenciaPendenteId = document.getElementById('ocorrenciaPendenteId').value;
              const novoCodigo = document.getElementById('novoCodigo').value;
              const novoTipo = document.getElementById('novoTipo').value;
              // Aqui você faria a chamada para a sua API para atribuir o código
              console.log('Atribuindo código:', ocorrenciaPendenteId, novoCodigo, novoTipo);
              // Após salvar, você pode fechar o modal e recarregar os dados
              const atribuirCodigoModal = bootstrap.Modal.getInstance(document.getElementById('atribuirCodigoModal'));
              atribuirCodigoModal.hide();
              loadOcorrencias();
              loadOcorrenciasPendentes();
          });
      }
  }

  // Inicializar
  init();
});