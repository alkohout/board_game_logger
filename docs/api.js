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

// Fetch an image the same way as everything else — with a bearer token — and
// hand back a blob URL. An <img src> can't carry an Authorization header, and
// making photos publicly addressable would undo the isolation everything else
// has.
const _blobCache = new Map();

async function apiImageUrl(path) {
    if (_blobCache.has(path)) return _blobCache.get(path);
    const r = await apiFetch(path);
    if (!r || !r.ok) return null;
    const url = URL.createObjectURL(await r.blob());
    _blobCache.set(path, url);
    return url;
}

function forgetImage(path) {
    const url = _blobCache.get(path);
    if (url) { URL.revokeObjectURL(url); _blobCache.delete(path); }
}

// Shrink a photo before it leaves the phone. A modern camera shot is 3-5 MB
// of detail nobody needs to see the state of a board, and uploading it over a
// mobile connection is the slow part.
const PHOTO_MAX_EDGE = 1600;

function shrinkImage(file, maxEdge = PHOTO_MAX_EDGE, quality = 0.82) {
    return new Promise(resolve => {
        const img = new Image();
        img.onload = () => {
            const scale = Math.min(1, maxEdge / Math.max(img.width, img.height));
            // Already small enough: don't re-encode and lose quality for nothing.
            if (scale === 1 && file.size <= 900 * 1024) { resolve(file); return; }
            const canvas = document.createElement('canvas');
            canvas.width = Math.round(img.width * scale);
            canvas.height = Math.round(img.height * scale);
            canvas.getContext('2d').drawImage(img, 0, 0, canvas.width, canvas.height);
            canvas.toBlob(
                blob => resolve(blob
                    ? new File([blob], 'photo.jpg', { type: 'image/jpeg' })
                    : file),
                'image/jpeg', quality);
        };
        img.onerror = () => resolve(file);   // not decodable here; let the server judge
        img.src = URL.createObjectURL(file);
    });
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
    let timer = null;
    const dismiss = () => { latest++; clearTimeout(timer); box.innerHTML = ''; };

    // Wait for a pause in typing before asking. Firing per keystroke sent six
    // requests for a six-letter game, and with only two server workers the one
    // that mattered — the last — queued behind its own predecessors. One
    // request after you stop typing is both fewer and sooner.
    const DEBOUNCE_MS = 200;

    input.addEventListener('input', () => {
        clearTimeout(timer);
        const term = input.value.trim();
        if (term.length < 2) { latest++; box.innerHTML = ''; return; }
        timer = setTimeout(() => search(term), DEBOUNCE_MS);
    });

    async function search(term) {
        const mine = ++latest;
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
    }

    document.addEventListener('click', e => { if (!input.contains(e.target)) dismiss(); });
}
