/**
 * Bizon Dark Editor - GUI JavaScript
 */

// API Base URL
const API_BASE = '';

// Current profile
let currentProfile = null;

// Translation map
const TR = {
    'gold': 'Złoto',
    'bust': 'Popiersia',
    'portrait': 'Portrety',
    'deed': 'Akty Nadania',
    'crest': 'Herby',
    'inraid': 'W Ekspedycji',
    'inbattle': 'W Walce',
    'teleported': 'Przeteleportowany',
    'dd_options_altered': 'Zmienione Opcje DD'
};

function t(key) {
    return TR[key.toLowerCase()] || key.charAt(0).toUpperCase() + key.slice(1);
}

/**
 * Helper to manage button loading states
 */
function setButtonLoading(button, isLoading, text = 'Przetwarzanie...') {
    if (isLoading) {
        button.dataset.originalText = button.innerHTML;
        button.innerHTML = `<span class="spinner"></span> ${text}`;
        button.disabled = true;
        button.classList.add('btn-loading');
    } else {
        button.innerHTML = button.dataset.originalText || button.innerHTML;
        button.disabled = false;
        button.classList.remove('btn-loading');
    }
}

// Tab switching
document.addEventListener('DOMContentLoaded', () => {
    initTabs();
    loadDashboard();
    loadAllData();
    initForms();
});

function initTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const tabId = btn.dataset.tab;
            
            // Update active states
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(tabId).classList.add('active');
            
            // Load data for specific tabs
            if (tabId === 'heroes') loadHeroes();
            if (tabId === 'upgrades') loadUpgrades();
            if (tabId === 'backup') loadBackups();
        });
    });
}

async function loadDashboard() {
    const container = document.getElementById('profile-status');
    
    try {
        const response = await fetch(`${API_BASE}/api/profile/status`);
        const data = await response.json();
        
        if (!response.ok) {
            container.innerHTML = `<div class="error">Błąd: ${data.detail || 'Nieznany błąd'}</div>`;
            return;
        }
        
        let html = `
            <div class="card">
                <h3>Profil: ${data.profile}</h3>
                <div class="data-grid">
                    <div class="data-item">
                        <label>Przedmioty w Trzosie:</label>
                        <value>${Object.keys(data.wallet).length}</value>
                    </div>
                    <div class="data-item">
                        <label>Bohaterowie:</label>
                        <value>${data.heroes?.length || 0}</value>
                    </div>
                    <div class="data-item">
                        <label>W Ekspedycji:</label>
                        <value>${data.game?.inraid === 1 ? 'Tak' : 'Nie'}</value>
                    </div>
                    <div class="data-item">
                        <label>W Walce:</label>
                        <value>${data.raid?.inbattle === 1 ? 'Tak' : 'Nie'}</value>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h3>Status Plików</h3>
        `;
        
        for (const [name, info] of Object.entries(data.files)) {
            const status = info.exists ? 'exists' : 'missing';
            const icon = info.exists ? '✓' : '✗';
            html += `
                <div class="file-status ${status}">
                    <span class="icon">${icon}</span>
                    <span>${name}: ${info.exists ? 'OK' : 'Brak'}</span>
                </div>
            `;
        }
        
        html += '</div>';
        container.innerHTML = html;
        
    } catch (error) {
        container.innerHTML = `<div class="error">Failed to load profile: ${error.message}</div>`;
    }
}

async function loadAllData() {
    await Promise.all([
        loadWallet(),
        loadGame(),
        loadRaid(),
    ]);
}

async function loadWallet() {
    const container = document.getElementById('wallet-content');
    
    try {
        const response = await fetch(`${API_BASE}/api/wallet`);
        const data = await response.json();
        
        if (!response.ok) {
            container.innerHTML = `<div class="error">${data.detail}</div>`;
            return;
        }
        
        let html = '<div class="data-grid">';
        for (const [key, value] of Object.entries(data)) {
            html += `
                <div class="data-item">
                    <label>${t(key)}:</label>
                    <value>${value.toLocaleString()}</value>
                </div>
            `;
        }
        html += '</div>';
        container.innerHTML = html;
        
        // Pre-fill form
        const form = document.getElementById('wallet-form');
        for (const [key, value] of Object.entries(data)) {
            const input = form.querySelector(`[name="${key}"]`);
            if (input) input.value = value;
        }
        
    } catch (error) {
        container.innerHTML = `<div class="error">Failed to load wallet: ${error.message}</div>`;
    }
}

async function loadHeroes() {
    const container = document.getElementById('heroes-content');
    container.innerHTML = '<div class="loading">Wczytywanie bohaterów...</div>';
    
    try {
        const response = await fetch(`${API_BASE}/api/heroes`);
        const data = await response.json();
        
        if (!response.ok) {
            container.innerHTML = `<div class="error">${data.detail}</div>`;
            return;
        }
        
        let html = '';
        data.heroes.forEach(hero => {
            html += `
                <div class="hero-card">
                    <div class="hero-header">
                        <span class="hero-name">${hero.name || 'Nieznany'}</span>
                        <span class="hero-class">${hero.class || 'Nieznany'}</span>
                    </div>
                    <div class="hero-stats">
                        <div class="hero-stat">
                            <span>Doświadczenie:</span>
                            <span>${hero.resolve_xp || 0}</span>
                        </div>
                        <div class="hero-stat">
                            <span>Poziom broni:</span>
                            <span>${hero.weapon_rank || 0}</span>
                        </div>
                        <div class="hero-stat">
                            <span>Poziom pancerza:</span>
                            <span>${hero.armour_rank || 0}</span>
                        </div>
                    </div>
                    <form class="hero-form" data-hero-index="${hero.hero_index}">
                        <div class="form-row">
                            <label for="hero-${hero.hero_index}-xp">Doświadczenie:</label>
                            <input type="number" id="hero-${hero.hero_index}-xp" name="resolve_xp" min="0" max="999999" value="${hero.resolve_xp || 0}">
                        </div>
                        <div class="form-row">
                            <label for="hero-${hero.hero_index}-weapon">Poziom broni:</label>
                            <input type="number" id="hero-${hero.hero_index}-weapon" name="weapon_rank" min="0" max="5" value="${hero.weapon_rank || 0}">
                        </div>
                        <div class="form-row">
                            <label for="hero-${hero.hero_index}-armour">Poziom pancerza:</label>
                            <input type="number" id="hero-${hero.hero_index}-armour" name="armour_rank" min="0" max="5" value="${hero.armour_rank || 0}">
                        </div>
                        <div class="form-actions">
                            <label class="checkbox">
                                <input type="checkbox" id="hero-${hero.hero_index}-dry-run" name="dry_run" checked> Symulacja
                            </label>
                            <button type="submit" class="btn btn-primary">Aktualizuj Bohatera</button>
                        </div>
                        <div class="hero-result-container" id="hero-result-${hero.hero_index}"></div>
                    </form>
                </div>
            `;
        });
        
        container.innerHTML = html;
        
        // Bind hero forms
        document.querySelectorAll('.hero-form').forEach(form => {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();
                const btn = e.target.querySelector('button[type="submit"]');
                setButtonLoading(btn, true);

                const heroIndex = form.dataset.heroIndex;
                const formData = new FormData(form);
                
                const updates = {};
                if (formData.get('resolve_xp')) updates.resolve_xp = parseInt(formData.get('resolve_xp'));
                if (formData.get('weapon_rank')) updates.weapon_rank = parseInt(formData.get('weapon_rank'));
                if (formData.get('armour_rank')) updates.armour_rank = parseInt(formData.get('armour_rank'));
                
                const dryRun = formData.get('dry_run') === 'on';
                
                try {
                    const response = await fetch(`${API_BASE}/api/heroes/${heroIndex}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                        body: new URLSearchParams({
                            ...updates,
                            dry_run: dryRun
                        })
                    });
                    
                    const result = await response.json();
                    
                    if (response.ok) {
                        showResult(`hero-result-${heroIndex}`, result, dryRun);
                        if (!dryRun) setTimeout(() => loadHeroes(), 2000);
                    } else {
                        showError(`hero-result-${heroIndex}`, result.detail);
                    }
                } catch (error) {
                    showError(`hero-result-${heroIndex}`, error.message);
                } finally {
                    setButtonLoading(btn, false);
                }
            });
        });
        
    } catch (error) {
        container.innerHTML = `<div class="error">Failed to load heroes: ${error.message}</div>`;
    }
}

async function loadUpgrades() {
    const container = document.getElementById('upgrades-content');
    container.innerHTML = '<div class="loading">Wczytywanie ulepszeń...</div>';
    
    try {
        const response = await fetch(`${API_BASE}/api/upgrades`);
        const data = await response.json();
        
        if (!response.ok) {
            container.innerHTML = `<div class="error">${data.detail}</div>`;
            return;
        }
        
        let html = `
            <div class="card">
                <h3>Podsumowanie</h3>
                <div class="data-grid">
                    <div class="data-item">
                        <label>Zakupy:</label>
                        <value>${data.purchases_count || 0}</value>
                    </div>
                    <div class="data-item">
                        <label>Zakupione:</label>
                        <value>${data.purchased_count || 0}</value>
                    </div>
                    <div class="data-item">
                        <label>Zniżki:</label>
                        <value>${data.discounts_count || 0}</value>
                    </div>
                </div>
            </div>
        `;
        
        if (data.classes) {
            html += '<div class="card"><h3>Klasy</h3>';
            for (const [cls, count] of Object.entries(data.classes)) {
                html += `
                    <div class="file-status exists">
                        <span class="icon">⚔️</span>
                        <span>${cls}: ${count} zakupów</span>
                    </div>
                `;
            }
            html += '</div>';
        }
        
        container.innerHTML = html;
        
    } catch (error) {
        container.innerHTML = `<div class="error">Failed to load upgrades: ${error.message}</div>`;
    }
}

async function loadGame() {
    const container = document.getElementById('game-content');
    
    try {
        const response = await fetch(`${API_BASE}/api/game`);
        const data = await response.json();
        
        if (!response.ok) {
            container.innerHTML = `<div class="error">${data.detail}</div>`;
            return;
        }
        
        let html = '<div class="data-grid">';
        for (const [key, value] of Object.entries(data)) {
            html += `
                <div class="data-item">
                    <label>${t(key)}:</label>
                    <value>${value === 1 ? 'Tak' : (value === 0 ? 'Nie' : value)}</value>
                </div>
            `;
        }
        html += '</div>';
        container.innerHTML = html;
        
    } catch (error) {
        container.innerHTML = `<div class="error">Failed to load game: ${error.message}</div>`;
    }
}

async function loadRaid() {
    const container = document.getElementById('raid-content');
    
    try {
        const response = await fetch(`${API_BASE}/api/raid`);
        const data = await response.json();
        
        if (!response.ok) {
            container.innerHTML = `<div class="error">${data.detail}</div>`;
            return;
        }
        
        let html = '<div class="data-grid">';
        for (const [key, value] of Object.entries(data)) {
            html += `
                <div class="data-item">
                    <label>${t(key)}:</label>
                    <value>${value === 1 ? 'Tak' : (value === 0 ? 'Nie' : value)}</value>
                </div>
            `;
        }
        html += '</div>';
        container.innerHTML = html;
        
    } catch (error) {
        container.innerHTML = `<div class="error">Failed to load raid: ${error.message}</div>`;
    }
}

async function loadBackups() {
    const backupsContainer = document.getElementById('backups-content');
    const presetsContainer = document.getElementById('presets-content');
    
    backupsContainer.innerHTML = '<div class="loading">Wczytywanie kopii...</div>';
    presetsContainer.innerHTML = '<div class="loading">Wczytywanie presetów...</div>';
    
    try {
        // Load backups
        const backupsResponse = await fetch(`${API_BASE}/api/backups`);
        const backupsData = await backupsResponse.json();
        
        if (backupsResponse.ok && backupsData.backups.length > 0) {
            let html = '';
            backupsData.backups.forEach(backup => {
                html += `
                    <div class="backup-item">
                        <span class="backup-path">${backup}</span>
                        <div class="backup-actions-inline">
                            <button class="btn btn-danger btn-sm" onclick="restoreBackup('${backup}', this)">Przywróć</button>
                        </div>
                    </div>
                `;
            });
            backupsContainer.innerHTML = html;
        } else {
            backupsContainer.innerHTML = '<div class="warning">Nie znaleziono żadnych kopii</div>';
        }
        
        // Load presets
        const presetsResponse = await fetch(`${API_BASE}/api/presets`);
        const presetsData = await presetsResponse.json();
        
        if (presetsResponse.ok) {
            let html = '<div class="preset-grid">';
            presetsData.presets.forEach(preset => {
                html += `
                    <div class="preset-card" onclick="applyPreset('${preset.name}')">
                        <h4>${preset.name}</h4>
                        <p>${preset.description}</p>
                    </div>
                `;
            });
            html += '</div>';
            presetsContainer.innerHTML = html;
        }
        
    } catch (error) {
        backupsContainer.innerHTML = `<div class="error">Failed to load backups: ${error.message}</div>`;
    }
}

function initForms() {
    // Wallet form
    document.getElementById('wallet-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = e.target.querySelector('button[type="submit"]');
        setButtonLoading(btn, true);
        const formData = new FormData(e.target);
        
        const params = new URLSearchParams();
        ['gold', 'bust', 'portrait', 'deed', 'crest'].forEach(key => {
            const value = formData.get(key);
            if (value !== '') params.append(key, value);
        });
        params.append('dry_run', formData.get('dry_run') === 'on');
        
        try {
            const response = await fetch(`${API_BASE}/api/wallet`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: params
            });
            
            const result = await response.json();
            
            if (response.ok) {
                showResult('wallet-result', result, formData.get('dry_run') === 'on');
                if (formData.get('dry_run') !== 'on') {
                    loadWallet();
                    loadDashboard();
                }
            } else {
                showError('wallet-result', result.detail);
            }
        } catch (error) {
            showError('wallet-result', error.message);
        } finally {
            setButtonLoading(btn, false);
        }
    });
    
    // Game form
    document.getElementById('game-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = e.target.querySelector('button[type="submit"]');
        setButtonLoading(btn, true);
        const formData = new FormData(e.target);
        
        const params = new URLSearchParams();
        ['inraid', 'dd_options_altered'].forEach(key => {
            const value = formData.get(key);
            if (value !== '') params.append(key, value);
        });
        params.append('dry_run', formData.get('dry_run') === 'on');
        
        try {
            const response = await fetch(`${API_BASE}/api/game`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: params
            });
            
            const result = await response.json();
            
            if (response.ok) {
                showResult('game-result', result, formData.get('dry_run') === 'on');
                if (formData.get('dry_run') !== 'on') {
                    loadGame();
                    loadDashboard();
                }
            } else {
                showError('game-result', result.detail);
            }
        } catch (error) {
            showError('game-result', error.message);
        } finally {
            setButtonLoading(btn, false);
        }
    });
    
    // Raid form
    document.getElementById('raid-form')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = e.target.querySelector('button[type="submit"]');
        setButtonLoading(btn, true);
        const formData = new FormData(e.target);
        
        const params = new URLSearchParams();
        if (formData.get('teleported') !== '') {
            params.append('teleported', formData.get('teleported'));
        }
        params.append('dry_run', formData.get('dry_run') === 'on');
        params.append('allow_inbattle', formData.get('allow_inbattle') === 'on');
        
        try {
            const response = await fetch(`${API_BASE}/api/raid`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: params
            });
            
            const result = await response.json();
            
            if (response.ok) {
                showResult('raid-result', result, formData.get('dry_run') === 'on');
                if (formData.get('dry_run') !== 'on') {
                    loadRaid();
                    loadDashboard();
                }
            } else {
                showError('raid-result', result.detail);
            }
        } catch (error) {
            showError('raid-result', error.message);
        } finally {
            setButtonLoading(btn, false);
        }
    });
    
    // Backup buttons
    document.getElementById('btn-create-backup')?.addEventListener('click', async (e) => {
        const btn = e.target;
        setButtonLoading(btn, true, 'Tworzenie...');
        try {
            const response = await fetch(`${API_BASE}/api/backups`, { method: 'POST' });
            const result = await response.json();
            
            if (response.ok) {
                alert(`Kopia utworzona: ${result.created}`);
                loadBackups();
            } else {
                alert(`Błąd: ${result.detail}`);
            }
        } catch (error) {
            alert(`Błąd: ${error.message}`);
        } finally {
            setButtonLoading(btn, false);
        }
    });
    
    document.getElementById('btn-refresh-backups')?.addEventListener('click', loadBackups);
}

async function restoreBackup(backupPath, btn) {
    if (!confirm('Czy na pewno chcesz przywrócić tę kopię? Obecny stan zostanie zapisany jako kopia bezpieczeństwa.')) {
        return;
    }
    
    if (btn) setButtonLoading(btn, true, 'Przywracanie...');

    try {
        const response = await fetch(`${API_BASE}/api/restore`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ backup_path: backupPath })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            alert(`Przywrócono pomyślnie! Kopia bezpieczeństwa: ${result.safety_backup || 'brak'}`);
            loadDashboard();
            loadAllData();
        } else {
            alert(`Błąd: ${result.detail}`);
        }
    } catch (error) {
        alert(`Błąd: ${error.message}`);
    } finally {
        if (btn) setButtonLoading(btn, false);
    }
}

async function applyPreset(name) {
    const dryRun = confirm('Zastosować preset w trybie symulacji (Dry Run)?\n\nOK = Symulacja\nAnuluj = Zastosuj natychmiast');
    
    try {
        const response = await fetch(`${API_BASE}/api/presets/apply`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({
                name: name,
                dry_run: dryRun // Fixed: confirm returns true for OK (Dry Run)
            })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            const mode = dryRun ? 'Symulacja zakończona' : 'Zastosowano';
            alert(`${mode}!\nLiczba operacji: ${result.operations.length}\n\nNotatki:\n${result.notes.join('\n')}`);
            
            if (!dryRun) {
                loadDashboard();
                loadAllData();
            }
        } else {
            alert(`Błąd: ${result.detail}`);
        }
    } catch (error) {
        alert(`Błąd: ${error.message}`);
    }
}

function showResult(containerId, result, dryRun) {
    const container = document.getElementById(containerId);
    const mode = dryRun ? 'SYMULACJA (DRY RUN)' : 'ZASTOSOWANO';
    
    let html = `<div class="${dryRun ? 'warning' : 'success'}">`;
    html += `<strong>${mode}</strong><br>`;
    html += `Operacje: ${result.operations.length}<br>`;
    
    if (result.operations.length > 0) {
        html += '<ul>';
        result.operations.forEach(op => {
            html += `<li>${op.key}: ${op.new_value}</li>`;
        });
        html += '</ul>';
    }
    
    html += '</div>';
    container.innerHTML = html;
}

function showError(containerId, message) {
    const container = document.getElementById(containerId);
    container.innerHTML = `<div class="error"><strong>Błąd:</strong> ${message}</div>`;
}
