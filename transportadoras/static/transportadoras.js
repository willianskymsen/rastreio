class TransportadorasManager {
    constructor() {
        this.state = {
            sistemasDisponiveis: [],
            transportadorasSelecionadas: [],
            transportadorasData: []
        };

        this.sortState = {
            column: null,
            direction: 'asc'
        };

        this.elements = {
            transportadorasTable: $('#transportadorasTable'),
            tableBody: $('#transportadorasTable tbody'),
            loadingSpinner: $('#loadingSpinner'),
            selecionarTodos: $('#selecionarTodos'),
            btnEditarMultiplo: $('#btnEditarMultiplo'),
            contadorSelecionados: $('#contadorSelecionados'),
            contadorModal: $('#contadorModal'),
            editTransportadoraId: $('#editTransportadoraId'),
            editSistema: $('#editSistema'),
            editSistemaMultiplo: $('#editSistemaMultiplo'),
            editarModal: new bootstrap.Modal('#editarTransportadoraModal'),
            editarMultiploModal: new bootstrap.Modal('#editarMultiploModal')
        };

        this.templates = {
            transportadoraRow: document.getElementById('transportadora-row-template'),
            emptyRow: document.getElementById('empty-row-template'),
            errorRow: document.getElementById('error-row-template'),
            toast: document.getElementById('toast-template')
        };

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.carregarTransportadoras();
        this.carregarOpcoesSistema();
    }

    setupEventListeners() {
        this.elements.selecionarTodos.on('change', () => this.toggleSelecionarTodos());
        this.elements.tableBody.on('change', '.transportadora-checkbox', () => this.atualizarSelecoes());
        this.elements.tableBody.on('click', '.btn-editar', (e) => {
            this.abrirModalEdicao($(e.currentTarget).data('id'));
        });
        this.elements.btnEditarMultiplo.on('click', () => this.abrirModalEdicaoMultipla());
        $('#salvarEdicaoBtn').on('click', () => this.handleSalvarEdicao());
        $('#salvarEdicaoMultiploBtn').on('click', () => this.handleSalvarEdicaoMultipla());

        // Eventos de ordenação
        this.elements.transportadorasTable.find('thead th.sortable').on('click', (e) => {
            const columnIndex = $(e.currentTarget).index();
            this.sortTable(columnIndex);
        });
    }

    async carregarTransportadoras() {
        this.showLoading(true);
        
        try {
            const response = await $.ajax({
                url: APP_CONFIG.urls.getTransportadoras,
                method: "GET",
                dataType: "json"
            });
            
            this.state.transportadorasData = response || [];
            this.renderTransportadoras();
        } catch (error) {
            this.renderError("Erro ao carregar dados");
            console.error("Erro ao carregar transportadoras:", error);
        } finally {
            this.showLoading(false);
        }
    }

    async carregarOpcoesSistema() {
        this.showLoading(true);
        
        try {
            const response = await $.ajax({
                url: APP_CONFIG.urls.getOpcoesSistema,
                method: "GET",
                dataType: "json"
            });
            this.state.sistemasDisponiveis = response.data || [];
            this.atualizarSelectSistemas();
            this.atualizarSelectSistemasMultiplo();
        } catch (error) {
            this.mostrarToast(`Erro ao carregar opções: ${error}`, "danger");
            console.error("Erro ao carregar opções do sistema:", error);
        } finally {
            this.showLoading(false);
        }
    }

    renderTransportadoras() {
        this.elements.tableBody.empty();
        
        if (!this.state.transportadorasData) {
            this.renderError("Resposta vazia da API");
            return;
        }
        
        if (this.state.transportadorasData.length) {
            const sortedData = this.sortData(this.state.transportadorasData);
            sortedData.forEach(transportadora => {
                this.renderTransportadoraRow(transportadora);
            });
        } else {
            this.renderEmpty("Nenhuma transportadora encontrada");
        }
        
        this.updateSortIndicators();
    }

    renderTransportadoraRow(transportadora) {
        const row = this.templates.transportadoraRow.content.cloneNode(true);
        const rowElement = $(row);
        
        rowElement.find('.transportadora-checkbox').data('id', transportadora.id);
        rowElement.find('.transportadora-id').text(transportadora.id || 'N/A');
        rowElement.find('.transportadora-nome').text(
            transportadora.descricao || transportadora.nome_fantasia || 'N/A'
        );
        rowElement.find('.transportadora-cnpj').text(
            transportadora.cnpj ? this.formatarCNPJ(transportadora.cnpj) : 'N/A'
        );
        rowElement.find('.transportadora-sistema').text(
            transportadora.sistema || "Não definido"
        );
        rowElement.find('.btn-editar').data('id', transportadora.id);
        
        this.elements.tableBody.append(rowElement);
    }

    renderError(message) {
        const row = this.templates.errorRow.content.cloneNode(true);
        const rowElement = $(row);
        rowElement.find('td').text(message);
        this.elements.tableBody.append(rowElement);
    }

    renderEmpty(message) {
        const row = this.templates.emptyRow.content.cloneNode(true);
        const rowElement = $(row);
        rowElement.find('td').text(message);
        this.elements.tableBody.append(rowElement);
    }

    sortTable(columnIndex) {
        if (this.sortState.column === columnIndex) {
            this.sortState.direction = this.sortState.direction === 'asc' ? 'desc' : 'asc';
        } else {
            this.sortState.column = columnIndex;
            this.sortState.direction = 'asc';
        }
        
        this.renderTransportadoras();
    }

    sortData(data) {
        if (this.sortState.column === null) {
            return data;
        }

        return [...data].sort((a, b) => {
            const colIndex = this.sortState.column - 1;
            
            let valueA, valueB;
            
            switch (colIndex) {
                case 0: // ID
                    valueA = a.id || 0;
                    valueB = b.id || 0;
                    break;
                case 1: // Nome
                    valueA = (a.descricao || a.nome_fantasia || '').toLowerCase();
                    valueB = (b.descricao || b.nome_fantasia || '').toLowerCase();
                    break;
                case 2: // CNPJ
                    valueA = a.cnpj || '';
                    valueB = b.cnpj || '';
                    break;
                case 3: // Sistema
                    valueA = a.sistema || '';
                    valueB = b.sistema || '';
                    break;
                default:
                    return 0;
            }
            
            if (colIndex === 0) {
                return this.sortState.direction === 'asc' 
                    ? valueA - valueB 
                    : valueB - valueA;
            }
            
            if (valueA < valueB) {
                return this.sortState.direction === 'asc' ? -1 : 1;
            }
            if (valueA > valueB) {
                return this.sortState.direction === 'asc' ? 1 : -1;
            }
            return 0;
        });
    }

    updateSortIndicators() {
        this.elements.transportadorasTable.find('thead th i.sort-icon').remove();
        this.elements.transportadorasTable.find('thead th').removeClass('sorted');
        
        if (this.sortState.column !== null) {
            const th = this.elements.transportadorasTable.find('thead th').eq(this.sortState.column);
            const iconClass = this.sortState.direction === 'asc' 
                ? 'bi bi-arrow-up-short' 
                : 'bi bi-arrow-down-short';
            
            th.append(` <i class="sort-icon ${iconClass}"></i>`);
            th.addClass('sorted');
        }
    }

    toggleSelecionarTodos() {
        const isChecked = this.elements.selecionarTodos.prop("checked");
        $(".transportadora-checkbox").prop("checked", isChecked);
        this.atualizarSelecoes();
    }

    atualizarSelecoes() {
        this.state.transportadorasSelecionadas = [];
        
        $(".transportadora-checkbox:checked").each((index, element) => {
            this.state.transportadorasSelecionadas.push($(element).data('id'));
        });
        
        this.atualizarContadores();
        this.elements.selecionarTodos.prop(
            "checked",
            $(".transportadora-checkbox").length === this.state.transportadorasSelecionadas.length
        );
    }

    atualizarContadores() {
        this.elements.contadorSelecionados.text(this.state.transportadorasSelecionadas.length);
        this.elements.contadorModal.text(this.state.transportadorasSelecionadas.length);
        this.elements.btnEditarMultiplo.toggleClass("d-none", this.state.transportadorasSelecionadas.length === 0);
    }

    abrirModalEdicao(id) {
        const row = $(`button[data-id="${id}"]`).closest("tr");
        
        this.elements.editTransportadoraId.val(id);
        this.elements.editSistema.val(this.getSistemaAtualId(
            row.find(".transportadora-sistema").text()
        ));
        
        $(".modal-title").text(`Editar Sistema - ${row.find(".transportadora-nome").text()}`);
        this.elements.editarModal.show();
    }

    abrirModalEdicaoMultipla() {
        if (this.state.transportadorasSelecionadas.length === 0) {
            this.mostrarToast("Selecione pelo menos uma transportadora", "warning");
            return;
        }

        this.elements.editSistemaMultiplo.val("");
        $(".modal-title-multiplo").text(
            `Editar Sistema (${this.state.transportadorasSelecionadas.length} transportadoras)`
        );
        this.elements.editarMultiploModal.show();
    }

    async handleSalvarEdicao() {
        const id = this.elements.editTransportadoraId.val();
        const sistemaId = this.elements.editSistema.val();
    
        if (!sistemaId) {
            this.mostrarToast("Por favor, selecione um sistema.", "warning");
            return;
        }
    
        await this.enviarAtualizacao([{ id: parseInt(id), sistema: sistemaId }], this.elements.editarModal);
    }

    async handleSalvarEdicaoMultipla() {
        const sistemaId = this.elements.editSistemaMultiplo.val();
    
        if (!sistemaId) {
            this.mostrarToast("Por favor, selecione um sistema.", "warning");
            return;
        }

        const alteracoes = this.state.transportadorasSelecionadas.map(id => ({
            id: parseInt(id),
            sistema: sistemaId
        }));

        this.showLoading(true);
        await this.enviarAtualizacao(alteracoes, this.elements.editarMultiploModal);
    }

    async enviarAtualizacao(alteracoes, modal) {
        try {
            const response = await $.ajax({
                url: APP_CONFIG.urls.atualizarSistema,
                method: "PUT",
                contentType: "application/json",
                data: JSON.stringify({ alteracoes })
            });
            this.handleUpdateResponse(response, alteracoes.length, modal);
        } catch (error) {
            this.mostrarToast(error.responseJSON?.error || "Erro ao atualizar sistema", "danger");
            console.error("Erro ao atualizar:", error);
        } finally {
            this.showLoading(false);
        }
    }

    handleUpdateResponse(response, count = 1, modal) {
        if (response?.success) {
            modal.hide();
            this.carregarTransportadoras();
            this.mostrarToast(
                response.message || 
                (count > 1 ? `Sistema atualizado para ${count} transportadoras!` : "Sistema atualizado com sucesso!"),
                "success"
            );
        } else {
            this.mostrarToast(response?.error || "Erro ao atualizar", "danger");
        }
    }

    formatarCNPJ(cnpj) {
        if (!cnpj) return '';
        const numeros = cnpj.toString().replace(/\D/g, '');
        const cnpjCompleto = numeros.padStart(14, '0');
        return cnpjCompleto.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, "$1.$2.$3/$4-$5");
    }

    getSistemaAtualId(sistemaAtual) {
        if (sistemaAtual === "Não definido") return "";
        const sistemaObj = this.state.sistemasDisponiveis.find(s => 
            s.valor === sistemaAtual || s.id == sistemaAtual
        );
        return sistemaObj?.id || '';
    }

    atualizarSelectSistemas() {
        this.atualizarSelect(this.elements.editSistema);
    }

    atualizarSelectSistemasMultiplo() {
        this.atualizarSelect(this.elements.editSistemaMultiplo);
    }

    atualizarSelect(selectElement) {
        selectElement.empty().append(
            $('<option></option>').val('').text('Selecione um sistema')
        );
        
        if (!this.state.sistemasDisponiveis.length) {
            selectElement.append(
                $('<option></option>').val('').text('Nenhuma opção cadastrada').prop('disabled', true)
            );
            return;
        }
        
        this.state.sistemasDisponiveis
            .sort((a, b) => (a.valor || '').localeCompare(b.valor || ''))
            .forEach(opcao => {
                if (opcao.id) {
                    const optionText = opcao.valor + (opcao.tipo ? ` (${opcao.tipo})` : '');
                    selectElement.append(
                        $('<option></option>').val(opcao.id).text(optionText)
                    );
                }
            });
    }

    mostrarToast(mensagem, tipo = "success") {
        const toastContent = this.templates.toast.content.cloneNode(true);
        const toastElement = $(toastContent);
        
        toastElement.addClass(`bg-${tipo}`);
        toastElement.find('.toast-body').text(mensagem);
        $("body").append(toastElement);
        
        const toast = new bootstrap.Toast(toastElement[0]);
        toast.show();
        
        toastElement.on('hidden.bs.toast', () => toastElement.remove());
    }

    showLoading(show) {
        this.elements.loadingSpinner.toggleClass('d-none', !show);
    }
}

// Inicializa a aplicação quando o DOM estiver pronto
$(document).ready(() => {
    new TransportadorasManager();
});