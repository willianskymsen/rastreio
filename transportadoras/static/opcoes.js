$(document).ready(function () {
    const opcoesTable = $("#opcoesTable tbody");
    const opcaoModal = new bootstrap.Modal("#opcaoModal");
    let editMode = false;

    // Carrega a lista de opções
    function carregarOpcoes() {
        showLoading(true);
        $.ajax({
            url: "/transportadoras/transportadoras/api/opcoes_sistema/listar",
            method: "GET",
            dataType: "json",
            success: function (response) {
                console.log("Resposta da API (opções):", response);
                opcoesTable.empty();

                // Extrai os dados considerando diferentes formatos de resposta
                const data = Array.isArray(response) ? response : 
                           (response.data || response.opcoes || []);

                if (data && data.length) {
                    data.forEach((opcao) => {
                        const ativo = opcao.ativo !== undefined ? opcao.ativo : true; // Default true se não informado
                        const row = `
                            <tr>
                                <td>${opcao.id || 'N/A'}</td>
                                <td>${opcao.tipo || 'N/A'}</td>
                                <td>${opcao.valor || 'N/A'}</td>
                                <td>
                                    <span class="status-badge ${ativo ? "badge-ativo" : "badge-inativo"}">
                                        ${ativo ? "Ativo" : "Inativo"}
                                    </span>
                                </td>
                                <td>
                                    <button class="btn btn-sm btn-primary btn-editar me-1" data-id="${opcao.id}">
                                        <i class="bi bi-pencil"></i> Editar
                                    </button>
                                    <button class="btn btn-sm btn-danger btn-excluir" data-id="${opcao.id}">
                                        <i class="bi bi-trash"></i> Excluir
                                    </button>
                                </td>
                            </tr>
                        `;
                        opcoesTable.append(row);
                    });
                } else {
                    opcoesTable.append(`
                        <tr>
                            <td colspan="5" class="text-center">Nenhuma opção encontrada</td>
                        </tr>
                    `);
                }

                // Adiciona eventos aos botões
                $(".btn-editar").click(function () {
                    const id = $(this).data("id");
                    abrirModalEdicao(id);
                });

                $(".btn-excluir").click(function () {
                    const id = $(this).data("id");
                    confirmarExclusao(id);
                });
            },
            error: function (error) {
                console.error("Erro ao carregar opções:", error);
                opcoesTable.append(`
                    <tr>
                        <td colspan="5" class="text-center text-danger">Erro ao carregar opções</td>
                    </tr>
                `);
                mostrarToast("Erro ao carregar opções. Consulte o console para detalhes.", "danger");
            },
            complete: function() {
                showLoading(false);
            }
        });
    }

    // Abre o modal para edição ou criação
    function abrirModalEdicao(id = null) {
        editMode = id !== null;

        if (editMode) {
            // Modo edição - carrega os dados da opção
            showLoading(true);
            $.ajax({
                url: `/transportadoras/transportadoras/api/opcoes_sistema/${id}`,
                method: "GET",
                dataType: "json",
                success: function (response) {
                    const opcao = response.data || response;
                    $("#opcaoId").val(opcao.id);
                    $("#opcaoTipo").val(opcao.tipo);
                    $("#opcaoValor").val(opcao.valor);
                    $("#opcaoAtivo").prop("checked", opcao.ativo !== undefined ? opcao.ativo : true);

                    $("#opcaoModalTitle").text("Editar Opção");
                    opcaoModal.show();
                },
                error: function (error) {
                    console.error("Erro ao carregar opção:", error);
                    mostrarToast("Erro ao carregar dados da opção", "danger");
                },
                complete: function() {
                    showLoading(false);
                }
            });
        } else {
            // Modo criação - limpa o formulário
            $("#opcaoId").val("");
            $("#opcaoTipo").val("");
            $("#opcaoValor").val("");
            $("#opcaoAtivo").prop("checked", true);

            $("#opcaoModalTitle").text("Nova Opção");
            opcaoModal.show();
        }
    }

    // Salva a opção (criação ou edição)
    $("#salvarOpcaoBtn").click(function () {
        const opcaoData = {
            tipo: $("#opcaoTipo").val().trim().toUpperCase(), // Força maiúsculas conforme tabela
            valor: $("#opcaoValor").val().trim(),
            ativo: $("#opcaoAtivo").is(":checked") ? 1 : 0 // Converte para tinyint (0 ou 1)
        };

        // Validação dos campos obrigatórios
        if (!opcaoData.tipo || !opcaoData.valor) {
            mostrarToast("Preencha todos os campos obrigatórios", "warning");
            return;
        }

        // Validação do tamanho dos campos conforme tabela
        if (opcaoData.tipo.length > 50) {
            mostrarToast("O campo Tipo deve ter no máximo 50 caracteres", "warning");
            return;
        }

        if (opcaoData.valor.length > 255) {
            mostrarToast("O campo Valor deve ter no máximo 255 caracteres", "warning");
            return;
        }

        const id = $("#opcaoId").val();
        showLoading(true);

        if (editMode) {
            // Edição com PUT
            $.ajax({
                url: `/transportadoras/transportadoras/api/opcoes_sistema/${id}`,
                method: "PUT",
                contentType: "application/json",
                data: JSON.stringify(opcaoData),
                success: function (response) {
                    opcaoModal.hide();
                    carregarOpcoes();
                    mostrarToast(response.message || "Opção atualizada com sucesso!", "success");
                },
                error: function (error) {
                    console.error("Erro ao atualizar opção:", error);
                    const errorMsg = error.responseJSON?.error || "Erro ao atualizar opção";
                    mostrarToast(errorMsg, "danger");
                },
                complete: function() {
                    showLoading(false);
                }
            });
        } else {
            // Criação com POST
            $.ajax({
                url: "/transportadoras/transportadoras/api/opcoes_sistema/criar",
                method: "POST",
                contentType: "application/json",
                data: JSON.stringify(opcaoData),
                success: function (response) {
                    opcaoModal.hide();
                    carregarOpcoes();
                    mostrarToast(response.message || "Opção criada com sucesso!", "success");
                },
                error: function (error) {
                    console.error("Erro ao criar opção:", error);
                    const errorMsg = error.responseJSON?.error || "Erro ao criar opção";
                    mostrarToast(errorMsg, "danger");
                },
                complete: function() {
                    showLoading(false);
                }
            });
        }
    });

    // Confirmação antes de excluir
    function confirmarExclusao(id) {
        const modalConfirmacao = new bootstrap.Modal(document.getElementById('confirmacaoExclusaoModal'));
        $('#confirmacaoExclusaoModal').data('id', id);
        modalConfirmacao.show();
    }

    // Exclui uma opção após confirmação
    $('#confirmarExclusaoBtn').click(function() {
        const id = $('#confirmacaoExclusaoModal').data('id');
        const modal = bootstrap.Modal.getInstance(document.getElementById('confirmacaoExclusaoModal'));
        modal.hide();
        
        showLoading(true);
        $.ajax({
            url: `/transportadoras/transportadoras/api/opcoes_sistema/${id}`,
            method: "DELETE",
            success: function (response) {
                carregarOpcoes();
                mostrarToast(response.message || "Opção excluída com sucesso!", "success");
            },
            error: function (error) {
                console.error("Erro ao excluir opção:", error);
                const errorMsg = error.responseJSON?.error || "Erro ao excluir opção";
                mostrarToast(errorMsg, "danger");
            },
            complete: function() {
                showLoading(false);
            }
        });
    });

    // Função para mostrar notificação toast
    function mostrarToast(mensagem, tipo = "success") {
        const toast = $(`
            <div class="toast align-items-center text-white bg-${tipo} border-0 position-fixed bottom-0 end-0 m-3" role="alert" aria-live="assertive" aria-atomic="true">
                <div class="d-flex">
                    <div class="toast-body">
                        ${mensagem}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                </div>
            </div>
        `);
        
        $("body").append(toast);
        const bsToast = new bootstrap.Toast(toast[0]);
        bsToast.show();
        
        toast.on("hidden.bs.toast", function() {
            toast.remove();
        });
    }

    // Mostra/oculta loading
    function showLoading(show) {
        if (show) {
            $('#loadingSpinner').removeClass('d-none');
        } else {
            $('#loadingSpinner').addClass('d-none');
        }
    }

    // Botão para nova opção
    $("#novaOpcaoBtn").click(function () {
        abrirModalEdicao();
    });

    // Inicialização
    carregarOpcoes();
});