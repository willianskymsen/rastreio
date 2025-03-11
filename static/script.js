document.addEventListener('DOMContentLoaded', function() {
    const fileLinks = document.querySelectorAll('.fileLink');
    const resultDiv = document.getElementById('result');

    fileLinks.forEach(link => {
        link.addEventListener('click', function(event) {
            event.preventDefault();
            const filename = this.getAttribute('data-filename');

            fetch('/api/dados', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ filename: filename })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    resultDiv.innerHTML = `<p class="error">${data.error}</p>`;
                } else {
                    resultDiv.innerHTML = `
                        <h2>Resultado:</h2>
                        <p><strong>Destinatário:</strong> ${data.destinatario}</p>
                        <p><strong>Número NF-e:</strong> ${data.nro_nf}</p>
                        <h3>Eventos:</h3>
                        <ul>
                            ${data.items.map(item => `
                                <li>
                                    <strong>Data/Hora:</strong> ${item.data_hora}<br>
                                    <strong>Ocorrência:</strong> ${item.ocorrencia}<br>
                                    <strong>Descrição:</strong> ${item.descricao}<br>
                                    <strong>Tipo:</strong> ${item.tipo}<br>
                                    <strong>Recebedor:</strong> ${item.nome_recebedor}
                                </li>
                            `).join('')}
                        </ul>
                    `;
                }
            })
            .catch(error => {
                console.error('Erro:', error);
            });
        });
    });
});