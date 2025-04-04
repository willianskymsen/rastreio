$(document).ready(function () {
    const categoryCardsContainer = $('#category-cards');
    const emptyCategory = $('#empty-category-state');
    const categoryCountBadge = $('#category-count');
    const ocorrenciasTableBody = $('#ocorrencias-table-body');
    const availableCountBadge = $('#available-count');
    const linkedOcorrenciasList = $('#linked-ocorrencias-list');
    const moveToRightBtn = $('#move-to-right-btn');
    const moveToLeftBtn = $('#move-to-left-btn');
    const moveAllRightBtn = $('#move-all-right-btn');
    const moveAllLeftBtn = $('#move-all-left-btn');
    const clearAllBtn = $('#clear-all-btn');
    const linkedCountBadge = $('#linked-count');
    const loadingOcorrenciasRow = $('#loading-ocorrencias-row');
    const errorOcorrenciasRow = $('#error-ocorrencias-row');
    const noOcorrenciasRow = $('#no-ocorrencias-row');
    const emptyLinkedList = $('#empty-linked-list');
    const novaCategoriaBtn = $('#nova-categoria-btn');
    const novaCategoriaModal = new bootstrap.Modal($('#novaCategoriaModal'));
    const confirmationModal = new bootstrap.Modal($('#confirmationModal'));
    const salvarVinculacoesBtn = $('#salvar-vinculacoes-btn');
    const selectedCategoryDisplay = $('#selected-category-display');
    const selectionStatus = $('#selection-status');
    const searchOcorrencias = $('#search-ocorrencias');
    const cardTemplate = document.querySelector('#category-card-template').content;

    let selectedCategory = null;
    let selectedOcorrenciaLeft = null;
    let selectedOcorrenciaRight = null;
    let linkedOcorrencias = [];
    let allOcorrencias = [];

    // Function to show a toast message
    function showToast(message, isSuccess = true) {
        const toastTemplate = $('#toast-template').clone();
        toastTemplate.removeAttr('id');
        toastTemplate.find('#toastMessage').text(message);

        if (!isSuccess) {
            toastTemplate.removeClass('bg-success').addClass('bg-danger');
        } else {
            toastTemplate.removeClass('bg-danger').addClass('bg-success');
        }

        $('.toast-container').append(toastTemplate);
        const toast = new bootstrap.Toast(toastTemplate[0], {
            delay: 3000
        });
        toast.show();

        // Remove toast from DOM after it's hidden
        toastTemplate.on('hidden.bs.toast', function () {
            $(this).remove();
        });
    }

    // Function to confirm action
    function confirmAction(message, callback) {
        $('#confirmation-message').text(message);
        $('#confirm-action-btn').off('click').on('click', function () {
            confirmationModal.hide();
            callback();
        });
        confirmationModal.show();
    }

    // Function to update UI states
    function updateUIState() {
        // Update category display
        if (selectedCategory) {
            selectedCategoryDisplay.html(`<i class="bi bi-folder-check me-1"></i>Categoria: <strong>${selectedCategory.name}</strong>`);
            selectionStatus.html(`Categoria selecionada: <strong>${selectedCategory.name}</strong>`);
        } else {
            selectedCategoryDisplay.html(`<i class="bi bi-folder me-1"></i>Nenhuma categoria selecionada`);
            selectionStatus.text('Nenhuma categoria selecionada');
        }

        // Update linked count
        linkedCountBadge.text(linkedOcorrencias.length);

        // Update buttons state
        moveToRightBtn.prop('disabled', !selectedCategory || !selectedOcorrenciaLeft ||
            linkedOcorrencias.some(item => item.codigo_ssw === selectedOcorrenciaLeft.codigo_ssw));
        moveToLeftBtn.prop('disabled', !selectedOcorrenciaRight);
        moveAllRightBtn.prop('disabled', !selectedCategory || allOcorrencias.length === 0);
        moveAllLeftBtn.prop('disabled', linkedOcorrencias.length === 0);
        clearAllBtn.prop('disabled', linkedOcorrencias.length === 0);
        salvarVinculacoesBtn.prop('disabled', linkedOcorrencias.length === 0 || selectedCategory === null);

        // Show/hide empty linked list message
        if (linkedOcorrencias.length > 0) {
            emptyLinkedList.addClass('d-none');
        } else {
            emptyLinkedList.removeClass('d-none');
        }
    }

    // Function to fetch and display category cards
    function fetchAndDisplayCategories() {
        categoryCardsContainer.find('.col:not(#empty-category-state)').remove();

        $.ajax({
            url: VINCULAR_CONFIG.urls.getCategorias,
            method: 'GET',
            dataType: 'json',
            success: function (data) {
                if (data && Array.isArray(data) && data.length > 0) {
                    emptyCategory.addClass('d-none');

                    data.forEach(category => {
                        const cardClone = document.importNode(cardTemplate, true);
                        const cardDiv = cardClone.querySelector('.category-card');
                        const cardTitle = cardClone.querySelector('.card-title');

                        cardDiv.dataset.categoryId = category.id;
                        cardDiv.dataset.categoryName = category.DESCRICAO;
                        cardTitle.textContent = category.DESCRICAO;

                        categoryCardsContainer.append(cardClone);
                    });

                    categoryCountBadge.text(data.length);

                    $('.category-card').off('click').on('click', function () {
                        $('.category-card').removeClass('selected');
                        $('.category-check').addClass('d-none');
                        $(this).addClass('selected');
                        $(this).find('.category-check').removeClass('d-none');

                        selectedCategory = {
                            id: $(this).data('category-id'),
                            name: $(this).data('category-name')
                        };

                        linkedOcorrenciasList.find(':not(#empty-linked-list)').remove();
                        linkedOcorrencias = [];
                        selectedOcorrenciaRight = null;
                        moveToLeftBtn.prop('disabled', true);
                        updateUIState();
                        showToast(`Categoria "${selectedCategory.name}" selecionada.`);

                        // Busca as ocorrências vinculadas para a categoria selecionada
                        $.ajax({
                            url: VINCULAR_CONFIG.urls.getCategorias + '/' + selectedCategory.id + '/ocorrencias',
                            method: 'GET',
                            dataType: 'json',
                            success: function (data) {
                                if (data && Array.isArray(data) && data.length > 0) {
                                    data.forEach(ocorrencia => {
                                        const newOcorrencia = {
                                            codigo_ssw: ocorrencia.CODIGO_SSW,
                                            descricao: ocorrencia.DESCRICAO
                                        };
                                        linkedOcorrencias.push(newOcorrencia);

                                        const listItem = document.createElement('li');
                                        listItem.classList.add('list-group-item', 'list-group-item-action');
                                        listItem.dataset.codigoSsw = newOcorrencia.codigo_ssw;
                                        listItem.dataset.descricao = newOcorrencia.descricao;

                                        const div = document.createElement('div');
                                        div.classList.add('d-flex', 'justify-content-between', 'align-items-center');

                                        const innerDiv = document.createElement('div');

                                        const span = document.createElement('span');
                                        span.classList.add('badge', 'bg-secondary', 'me-2');
                                        span.textContent = newOcorrencia.codigo_ssw;

                                        const descricaoText = document.createTextNode(newOcorrencia.descricao);

                                        innerDiv.appendChild(span);
                                        innerDiv.appendChild(descricaoText);
                                        div.appendChild(innerDiv);
                                        listItem.appendChild(div);

                                        linkedOcorrenciasList.append(listItem);
                                    });
                                    updateUIState();
                                } else {
                                    updateUIState();
                                }
                            },
                            error: function (error) {
                                console.error("Erro ao buscar ocorrências vinculadas:", error);
                                showToast("Erro ao carregar as ocorrências vinculadas.", false);
                            }
                        });
                    });
                } else {
                    emptyCategory.removeClass('d-none');
                    categoryCountBadge.text('0');
                }
            },
            error: function (error) {
                console.error("Erro ao buscar categorias:", error);
                showToast("Erro ao carregar as categorias.", false);
                emptyCategory.removeClass('d-none').find('.empty-state p').text('Erro ao carregar categorias');
                categoryCountBadge.text('0');
            }
        });
    }

    // Function to fetch and display occurrences
    function fetchAndDisplayOcorrencias() {
        loadingOcorrenciasRow.removeClass('d-none');
        errorOcorrenciasRow.addClass('d-none');
        noOcorrenciasRow.addClass('d-none');
        ocorrenciasTableBody.find('tr:not(#loading-ocorrencias-row):not(#error-ocorrencias-row):not(#no-ocorrencias-row)').remove();

        $.ajax({
            url: VINCULAR_CONFIG.urls.getOcorrencias,
            method: 'GET',
            dataType: 'json',
            success: function (data) {
                loadingOcorrenciasRow.addClass('d-none');
                if (data && data.length > 0) {
                    allOcorrencias = data;
                    availableCountBadge.text(data.length);

                    data.forEach(ocorrencia => {
                        const row = document.createElement('tr');
                        row.dataset.codigoSsw = ocorrencia.CODIGO_SSW;
                        row.dataset.descricao = ocorrencia.DESCRICAO;

                        const codigoTd = document.createElement('td');
                        codigoTd.classList.add('align-middle');
                        codigoTd.textContent = ocorrencia.CODIGO_SSW;

                        const descricaoTd = document.createElement('td');
                        descricaoTd.classList.add('align-middle');
                        descricaoTd.textContent = ocorrencia.DESCRICAO;

                        row.appendChild(codigoTd);
                        row.appendChild(descricaoTd);
                        ocorrenciasTableBody.append(row);
                    });

                    $('#ocorrencias-table-body tr:not(#loading-ocorrencias-row):not(#error-ocorrencias-row):not(#no-ocorrencias-row)').off('click').on('click', function () {
                        $('#ocorrencias-table-body tr').removeClass('table-primary');
                        $(this).addClass('table-primary');

                        selectedOcorrenciaLeft = {
                            codigo_ssw: $(this).data('codigo-ssw'),
                            descricao: $(this).data('descricao')
                        };

                        selectedOcorrenciaRight = null;
                        $('#linked-ocorrencias-list .list-group-item.active').removeClass('active');

                        updateUIState();
                    });

                    updateUIState();
                } else {
                    noOcorrenciasRow.removeClass('d-none');
                    availableCountBadge.text('0');
                }
            },
            error: function (error) {
                loadingOcorrenciasRow.addClass('d-none');
                errorOcorrenciasRow.removeClass('d-none');
                console.error("Erro ao buscar ocorrências:", error);
                showToast("Erro ao carregar as ocorrências.", false);
                availableCountBadge.text('0');
            }
        });
    }

    // Search/filter functionality
    searchOcorrencias.on('input', function () {
        const searchTerm = $(this).val().toLowerCase();

        $('#ocorrencias-table-body tr:not(#loading-ocorrencias-row):not(#error-ocorrencias-row):not(#no-ocorrencias-row)').each(function () {
            const codigo = $(this).data('codigo-ssw').toString().toLowerCase();
            const descricao = $(this).data('descricao').toString().toLowerCase();

            if (codigo.includes(searchTerm) || descricao.includes(searchTerm)) {
                $(this).show();
            } else {
                $(this).hide();
            }
        });
    });

    // Move occurrence from left to right
    moveToRightBtn.on('click', function () {
        if (selectedCategory && selectedOcorrenciaLeft) {
            if (!linkedOcorrencias.some(item => item.codigo_ssw === selectedOcorrenciaLeft.codigo_ssw)) {
                linkedOcorrencias.push(selectedOcorrenciaLeft);

                const listItem = document.createElement('li');
                listItem.classList.add('list-group-item', 'list-group-item-action');
                listItem.dataset.codigoSsw = selectedOcorrenciaLeft.codigo_ssw;
                listItem.dataset.descricao = selectedOcorrenciaLeft.descricao;

                const div = document.createElement('div');
                div.classList.add('d-flex', 'justify-content-between', 'align-items-center');

                const innerDiv = document.createElement('div');

                const span = document.createElement('span');
                span.classList.add('badge', 'bg-secondary', 'me-2');
                span.textContent = selectedOcorrenciaLeft.codigo_ssw;

                const descricaoText = document.createTextNode(selectedOcorrenciaLeft.descricao);

                innerDiv.appendChild(span);
                innerDiv.appendChild(descricaoText);
                div.appendChild(innerDiv);
                listItem.appendChild(div);

                linkedOcorrenciasList.append(listItem);

                // Remove highlighting and the row from the left table
                $('#ocorrencias-table-body tr.table-primary').remove();
                selectedOcorrenciaLeft = null;

                updateUIState();
                showToast("Ocorrência adicionada com sucesso!");
            } else {
                showToast("Esta ocorrência já está vinculada.", false);
            }
        } else if (!selectedCategory) {
            showToast("Por favor, selecione uma categoria primeiro.", false);
        } else {
            showToast("Por favor, selecione uma ocorrência na tabela à esquerda.", false);
        }
    });

    // Move occurrence from right to left
    moveToLeftBtn.on('click', function () {
        if (selectedOcorrenciaRight) {
            linkedOcorrencias = linkedOcorrencias.filter(item => item.codigo_ssw !== selectedOcorrenciaRight.codigo_ssw);
            linkedOcorrenciasList.find(`[data-codigo-ssw="${selectedOcorrenciaRight.codigo_ssw}"]`).remove();

            selectedOcorrenciaRight = null;
            updateUIState();
            showToast("Ocorrência removida com sucesso.");

            // Recarrega as ocorrências disponíveis para exibir a que foi removida
            fetchAndDisplayOcorrencias();
        } else {
            showToast("Por favor, selecione uma ocorrência na lista à direita.", false);
        }
    });

    // Move all occurrences from left to right
    moveAllRightBtn.on('click', function () {
        if (selectedCategory) {
            if (allOcorrencias.length > 0) {
                confirmAction("Deseja vincular todas as ocorrências disponíveis à categoria?", function () {
                    let addedCount = 0;

                    allOcorrencias.forEach(ocorrencia => {
                        if (!linkedOcorrencias.some(item => item.codigo_ssw === ocorrencia.CODIGO_SSW)) {
                            const newOcorrencia = {
                                codigo_ssw: ocorrencia.CODIGO_SSW,
                                descricao: ocorrencia.DESCRICAO
                            };

                            linkedOcorrencias.push(newOcorrencia);

                            const listItem = document.createElement('li');
                            listItem.classList.add('list-group-item', 'list-group-item-action');
                            listItem.dataset.codigoSsw = newOcorrencia.codigo_ssw;
                            listItem.dataset.descricao = newOcorrencia.descricao;

                            const div = document.createElement('div');
                            div.classList.add('d-flex', 'justify-content-between', 'align-items-center');

                            const innerDiv = document.createElement('div');

                            const span = document.createElement('span');
                            span.classList.add('badge', 'bg-secondary', 'me-2');
                            span.textContent = newOcorrencia.codigo_ssw;

                            const descricaoText = document.createTextNode(newOcorrencia.descricao);

                            innerDiv.appendChild(span);
                            innerDiv.appendChild(descricaoText);
                            div.appendChild(innerDiv);
                            listItem.appendChild(div);

                            linkedOcorrenciasList.append(listItem);
                            addedCount++;
                        }
                    });

                    // Remove highlighting from the left table
                    $('#ocorrencias-table-body tr.table-primary').removeClass('table-primary');
                    selectedOcorrenciaLeft = null;

                    updateUIState();

                    if (addedCount > 0) {
                        showToast(`${addedCount} ocorrência(s) adicionada(s) com sucesso!`);
                    } else {
                        showToast("Todas as ocorrências já estão vinculadas.", false);
                    }
                });
            } else {
                showToast("Não há ocorrências disponíveis para vincular.", false);
            }
        } else {
            showToast("Por favor, selecione uma categoria primeiro.", false);
        }
    });

    // Remove all occurrences from right
    moveAllLeftBtn.on('click', function () {
        if (linkedOcorrencias.length > 0) {
            confirmAction("Deseja remover todas as ocorrências vinculadas?", function () {
                linkedOcorrencias = [];
                linkedOcorrenciasList.find('.list-group-item:not(#empty-linked-list)').remove();
                selectedOcorrenciaRight = null;
                updateUIState();
                showToast("Todas as ocorrências foram removidas.");
            });
        } else {
            showToast("Não há ocorrências vinculadas para remover.", false);
        }
    });

    // Clear all linked occurrences
    clearAllBtn.on('click', function () {
        if (linkedOcorrencias.length > 0) {
            confirmAction("Deseja limpar todas as ocorrências vinculadas?", function () {
                linkedOcorrencias = [];
                linkedOcorrenciasList.find('.list-group-item:not(#empty-linked-list)').remove();
                selectedOcorrenciaRight = null;
                updateUIState();
                showToast("Todas as ocorrências foram removidas.");
            });
        } else {
            showToast("Não há ocorrências vinculadas para remover.", false);
        }
    });

    // Handle form submission inside the modal
    $('#salvarNovaCategoriaBtn').off('click').on('click', function (event) {
        event.preventDefault(); // Prevent default form submission
        const descricaoCategoria = $('#descricaoCategoria').val().trim();

        if (descricaoCategoria) {
            $.ajax({
                url: VINCULAR_CONFIG.urls.getCategorias,
                method: 'POST',
                dataType: 'json',
                contentType: 'application/json',
                data: JSON.stringify({ descricao: descricaoCategoria }),
                success: function (response) {
                    showToast('Categoria salva com sucesso!');
                    novaCategoriaModal.hide();
                    fetchAndDisplayCategories(); // Reload categories after adding
                    $('#novaCategoriaForm')[0].reset(); // Clear the form
                },
                error: function (error) {
                    console.error("Erro ao salvar categoria:", error);
                    showToast('Erro ao salvar categoria.', false);
                }
            });
        } else {
            showToast('Por favor, preencha a descrição da categoria.', false);
        }
    });

    // Event listener for saving the vinculações
    salvarVinculacoesBtn.on('click', function () {
        if (selectedCategory && linkedOcorrencias.length > 0) {
            confirmAction(`Deseja salvar a vinculação de ${linkedOcorrencias.length} ocorrência(s) à categoria "${selectedCategory.name}"?`, function () {
                const ocorrenciasParaVincular = linkedOcorrencias.map(oco => oco.codigo_ssw);

                $.ajax({
                    url: VINCULAR_CONFIG.urls.vincularOcorrencia,
                    method: 'PUT',
                    dataType: 'json',
                    contentType: 'application/json',
                    data: JSON.stringify({
                        categoria_id: selectedCategory.id,
                        ocorrencias: ocorrenciasParaVincular
                    }),
                    success: function (response) {
                        showToast('Vinculações salvas com sucesso!');

                        // Reset state
                        linkedOcorrencias = [];
                        linkedOcorrenciasList.find('.list-group-item:not(#empty-linked-list)').remove();

                        // Reset UI
                        $('.category-card.selected').removeClass('selected');
                        $('.category-check').addClass('d-none');
                        selectedCategory = null;
                        selectedOcorrenciaLeft = null;
                        selectedOcorrenciaRight = null;

                        updateUIState();

                        // Optionally reload data
                        fetchAndDisplayOcorrencias();
                    },
                    error: function (error) {
                        console.error("Erro ao salvar vinculações:", error);
                        showToast('Erro ao salvar vinculações.', false);
                    }
                });
            });
        } else if (!selectedCategory) {
            showToast('Por favor, selecione uma categoria.', false);
        } else {
            showToast('Por favor, vincule pelo menos uma ocorrência.', false);
        }
    });

    // Event listener for clicks on linked occurrences
    linkedOcorrenciasList.on('click', '.list-group-item', function () {
        $('#linked-ocorrencias-list .list-group-item').removeClass('active');
        $(this).addClass('active');

        selectedOcorrenciaRight = {
            codigo_ssw: $(this).data('codigo-ssw'),
            descricao: $(this).data('descricao')
        };

        selectedOcorrenciaLeft = null;
        $('#ocorrencias-table-body tr.table-primary').removeClass('table-primary');

        updateUIState();
    });

    // Retry button for loading occurrences
    $('#retry-load-btn').on('click', function () {
        fetchAndDisplayOcorrencias();
    });

    // Function to open the new category form (modal)
    novaCategoriaBtn.on('click', function () {
        $('#novaCategoriaForm')[0].reset();
        novaCategoriaModal.show();
    });

    // Initial data loading
    fetchAndDisplayCategories();
    fetchAndDisplayOcorrencias();
});