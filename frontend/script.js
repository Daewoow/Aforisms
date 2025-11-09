const frontendVersionEl = document.querySelector('.frontend-version');

async function loadFrontendVersion() {
    try {
        const resp = await fetch('/version.json', { cache: 'no-cache' });
        if (!resp.ok)
            return;
        const j = await resp.json();
        frontendVersionEl.textContent = `Фронтенд: ${j.frontend_version || '-'}`;
    } catch (e) {
        console.warn('Не удалось получить версию фронта', e);
    }
}

loadFrontendVersion();

document.addEventListener('DOMContentLoaded', function() {
    const textInput = document.getElementById('textInput');
    const searchBtn = document.getElementById('searchBtn');
    const resultsContainer = document.getElementById('results');
    const backendVersionEl = document.getElementById('backendVersion');
    const backendIdEl = document.getElementById('backendId');

    const addTypeSelect = document.getElementById('addTypeSelect');
    const aforismFields = document.getElementById('aforismFields');
    const wordFields = document.getElementById('wordFields');

    const newPhraseInput = document.getElementById('newPhrase');
    const phraseAuthorInput = document.getElementById('phraseAuthor');
    const phraseDescriptionInput = document.getElementById('phraseDescription');

    const newWordInput = document.getElementById('newWord');
    const wordDescriptionInput = document.getElementById('wordDescription');

    const addBtn = document.getElementById('addBtn');
    const addStatus = document.getElementById('addStatus');

    addTypeSelect.addEventListener('change', () => {
        if (addTypeSelect.value === 'aforism') {
            aforismFields.style.display = 'block';
            wordFields.style.display = 'none';
        } else {
            aforismFields.style.display = 'none';
            wordFields.style.display = 'block';
        }
    });

    async function searchPhrases() {
        const text = textInput.value.trim();
        if (!text) {
            showError('Пожалуйста, введите текст для поиска');
            return;
        }
        showLoading();
        const queryText = encodeURIComponent(text);

        try {
            const [phraseResponse, wordResponse] = await Promise.all([
                fetch(`/phrase?text=${queryText}`, {
                    method: 'GET',
                    headers: { 'Content-Type': 'application/json' }
                }),
                fetch(`/word?text=${queryText}`, {
                    method: 'GET',
                    headers: { 'Content-Type': 'application/json' }
                })
            ]);

            if (!phraseResponse.ok || !wordResponse.ok) {
                throw new Error('Ошибка при поиске');
            }

            const phraseData = await phraseResponse.json();
            const wordData = await wordResponse.json();
            const normalizedResults = [];

            (phraseData.phrases || []).forEach(p => normalizedResults.push({
                type: 'aforism',
                text: p.phrase,
                subtext: `— ${p.author}`,
                description: p.description,
                similarity: p.similarity_score
            }));

            (wordData.words || []).forEach(w => normalizedResults.push({
                type: 'word',
                text: w.word,
                subtext: w.description,
                description: null,
                similarity: w.similarity_score
            }));

            normalizedResults.sort((a, b) => b.similarity - a.similarity);
            backendVersionEl.textContent = phraseData.backend_version || '-';
            backendIdEl.textContent = phraseData.backend_id || '-';

            displayResults(normalizedResults, text);

        } catch (error) {
            showError('Ошибка: ' + error.message);
            console.error('Search error:', error);
        }
    }

    async function addNewEntry() {
        const type = addTypeSelect.value;
        let apiUrl = '';
        let payload = {};

        if (type === 'aforism') {
            const phrase = newPhraseInput.value.trim();
            const author = phraseAuthorInput.value.trim();
            const description = phraseDescriptionInput.value.trim();

            if (!phrase || !author) {
                showAddStatus('Текст фразы и автор обязательны!', 'error');
                return;
            }
            apiUrl = '/phrase';
            payload = { phrase, author, description: description || ' ' };

        } else {
            const word = newWordInput.value.trim();
            const description = wordDescriptionInput.value.trim();

            if (!word || !description) {
                showAddStatus('Слово и его описание обязательны!', 'error');
                return;
            }
            apiUrl = '/word';
            payload = { word, description };
        }

        try {
            addStatus.textContent = 'Добавление...';
            addStatus.className = '';

            const response = await fetch(apiUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await response.json();

            if (response.ok) {
                showAddStatus('Успешно добавлено!', 'success');
                newPhraseInput.value = '';
                phraseAuthorInput.value = '';
                phraseDescriptionInput.value = '';
                newWordInput.value = '';
                wordDescriptionInput.value = '';

                setTimeout(() => {
                    addStatus.textContent = '';
                    addStatus.className = '';
                }, 2000);
            } else {
                showAddStatus(data.error || 'Ошибка при добавлении', 'error');
            }
        } catch (error) {
            showAddStatus('Ошибка сети: ' + error.message, 'error');
            console.error('Add entry error:', error);
        }
    }

    function showLoading() {
        resultsContainer.innerHTML = `<div class="loading">Ищем похожие фразы и слова...</div>`;
    }

    function displayResults(results, queryText) {
        if (!results || results.length === 0) {
            resultsContainer.innerHTML = `<div class="error"><p>Похожих фраз или слов не найдено</p></div>`;
            return;
        }

        let html = `
            <div class="search-summary">
                <h3>Найдено ${results.length} рез. для: "${queryText}"</h3>
                <hr style="margin: 15px 0;">
            </div>
        `;

        results.forEach(item => {
            if (item.type === 'aforism') {
                html += `
                    <div class="phrase-card">
                        <div class="card-type-label">Афоризм</div>
                        <div class="phrase-text">"${item.text}"</div>
                        <div class="phrase-author">${item.subtext}</div>
                        ${item.description ? `<div class="phrase-source">(${item.description})</div>` : ''}
                        <div class="similarity-score">
                            Сходство: ${(item.similarity * 100).toFixed(1)}%
                        </div>
                    </div>
                `;
            } else if (item.type === 'word') {
                html += `
                    <div class="phrase-card word-card"> <div class="card-type-label">Слово</div>
                        <div class="phrase-text">${item.text}</div>
                        <div class="phrase-author">${item.subtext}</div> <div class="similarity-score">
                            Сходство: ${(item.similarity * 100).toFixed(1)}%
                        </div>
                    </div>
                `;
            }
        });

        resultsContainer.innerHTML = html;
    }

    function showError(message) {
        resultsContainer.innerHTML = `<div class="error"><p>${message}</p></div>`;
    }

    function showAddStatus(message, type) {
        addStatus.textContent = message;
        addStatus.className = type;
    }

    searchBtn.addEventListener('click', searchPhrases);
    textInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            searchPhrases();
        }
    });

    addBtn.addEventListener('click', addNewEntry);

    resultsContainer.innerHTML = `
        <div class="placeholder">
            <p>Введите текст и нажмите "Найти"</p>
            <p style="margin-top: 10px; color: #668;">Например: "время лечит", "опытный человек", "любовь"</p>
        </div>
    `;
});