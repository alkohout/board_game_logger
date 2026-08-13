// Shared tab bar. Most tabs show a panel on the dashboard; Rules is its own
// page, so selecting it navigates there — the bar stays put either way, so
// the Rules Assistant feels like part of the app rather than somewhere you
// were sent.

const TABS = [
    { name: 'log',     label: 'Log' },
    { name: 'stats',   label: 'Stats' },
    { name: 'games',   label: 'Games' },
    { name: 'rules',   label: 'Rules', page: './rules_assistant.html' },
    { name: 'query',   label: 'Query', page: './database_query.html' },
    { name: 'tools',   label: 'Tools' },
    { name: 'account', label: 'Account' },
];
const TAB_KEY = 'bg_tab';

function renderTabs(active) {
    const mount = document.getElementById('tabbar-mount');
    if (!mount) return;
    mount.innerHTML = '<div class="tabs">' + TABS.map(t =>
        `<button class="tab${t.name === active ? ' active' : ''}" data-tab="${t.name}">${t.label}</button>`
    ).join('') + '</div>';
    mount.querySelectorAll('.tab').forEach(b =>
        b.addEventListener('click', () => selectTab(b.dataset.tab)));
}

function selectTab(name) {
    if (name === 'ai') name = 'rules';                 // the tab this replaced
    const tab = TABS.find(t => t.name === name) || TABS[0];
    localStorage.setItem(TAB_KEY, tab.name);
    if (tab.page) {                                     // a tab that is a page
        if (!window.location.pathname.endsWith(tab.page.replace('./', ''))) {
            window.location.href = tab.page;
        }
        return;
    }
    if (typeof window.showPanel === 'function') {       // we're on the dashboard
        window.showPanel(tab.name);
        renderTabs(tab.name);
    } else {
        window.location.href = './dashboard.html';      // panels live there
    }
}

function rememberedTab() {
    return localStorage.getItem(TAB_KEY) || 'log';
}
