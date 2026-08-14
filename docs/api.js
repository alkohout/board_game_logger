// Shared auth + fetch helpers. Requires config.js loaded first.

function getToken() {
    return localStorage.getItem('bg_token');
}

function requireAuth() {
    if (!getToken()) {
        window.location.href = './index.html';
        throw new Error('Not authenticated');
    }
}

function logout() {
    localStorage.removeItem('bg_token');
    window.location.href = './index.html';
}

async function apiFetch(path, options = {}) {
    const token = getToken();
    const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
    if (token) headers['Authorization'] = 'Bearer ' + token;

    const resp = await fetch(API_BASE + path, { ...options, headers });

    if (resp.status === 401) {
        localStorage.removeItem('bg_token');
        window.location.href = './index.html';
        return null;
    }
    return resp;
}

async function apiGet(path) {
    const r = await apiFetch(path);
    if (!r) return null;
    return r.json();
}

async function apiPost(path, body) {
    const r = await apiFetch(path, { method: 'POST', body: JSON.stringify(body) });
    if (!r) return null;
    return r.json();
}

// Upload with multipart (for rulebook PDF)
async function apiUpload(path, formData) {
    try {
        const token = getToken();
        const headers = {};
        if (token) headers['Authorization'] = 'Bearer ' + token;
        const resp = await fetch(API_BASE + path, { method: 'POST', headers, body: formData });
        if (resp.status === 401) {
            localStorage.removeItem('bg_token');
            window.location.href = './index.html';
            return null;
        }
        if (resp.status === 413) {
            return { success: false, message: 'File too large — try a smaller PDF.' };
        }
        return await resp.json();
    } catch (e) {
        console.error('apiUpload failed for', path, e);
        return { success: false, message: 'Upload failed: ' + e.message };
    }
}

// Autocomplete helper
function setupAutocomplete(inputId, suggestionsId, onSelect) {
    const input = document.getElementById(inputId);
    const box = document.getElementById(suggestionsId);
    if (!input || !box) return;

    // Every keystroke starts a request, and they don't come back in order.
    // Without this counter, picking a suggestion clears the list and then an
    // older reply lands and draws it again — once per request still in flight,
    // which is why a fast typist saw the dropdown reopen several times over.
    // Bumping `latest` invalidates everything outstanding.
    let latest = 0;
    const dismiss = () => { latest++; box.innerHTML = ''; };

    input.addEventListener('input', async () => {
        const mine = ++latest;
        const term = input.value.trim();
        if (term.length < 2) { box.innerHTML = ''; return; }
        const data = await apiGet('/search_games?term=' + encodeURIComponent(term));
        if (mine !== latest) return;      // superseded while we waited
        box.innerHTML = '';
        (data?.suggestions || []).forEach(s => {
            const div = document.createElement('div');
            div.className = 'autocomplete-suggestion';
            div.textContent = s;
            div.addEventListener('click', () => {
                input.value = s;
                dismiss();
                // Setting .value in code fires no event, so anything watching
                // the field has to be told by hand.
                input.dispatchEvent(new Event('change', { bubbles: true }));
                if (onSelect) onSelect(s);
            });
            box.appendChild(div);
        });
    });
    document.addEventListener('click', e => { if (!input.contains(e.target)) dismiss(); });
}
