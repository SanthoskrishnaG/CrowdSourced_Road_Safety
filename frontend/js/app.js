const API_BASE_URL = 'http://localhost:8000/api/v1';

// Category Emoji & Labels Map
const CATEGORY_ICONS = {
    'POTHOLE': '🕳️',
    'ROAD_DAMAGE': '⚠️',
    'BROKEN_STREETLIGHT': '💡',
    'BLOCKED_ROAD': '🚧',
    'GARBAGE': '🗑️',
    'FLOODING': '🌊',
    'DAMAGED_SIGN': '🛑',
    'OBSTRUCTION': '🌲',
    'OTHER': '📌'
};

const CATEGORY_NAMES = {
    'POTHOLE': 'Pothole',
    'ROAD_DAMAGE': 'Road Damage',
    'BROKEN_STREETLIGHT': 'Broken Streetlight',
    'BLOCKED_ROAD': 'Blocked Road',
    'GARBAGE': 'Garbage / Debris',
    'FLOODING': 'Flooding',
    'DAMAGED_SIGN': 'Damaged Road Sign',
    'OBSTRUCTION': 'Obstruction',
    'OTHER': 'Other Hazard'
};

const DEPARTMENT_NAMES = {
    'ROAD_DEPARTMENT': 'Roads & Highways',
    'ELECTRICAL_DEPARTMENT': 'Electrical & Lighting',
    'SANITATION_DEPARTMENT': 'Sanitation & Waste',
    'TRAFFIC_DEPARTMENT': 'Traffic Management',
    'DRAINAGE_DEPARTMENT': 'Storm Drainage',
    'GENERAL_WORKS': 'General Public Works'
};

// Global App State
let authToken = localStorage.getItem('roadops_auth_token') || '';
let currentUserRole = localStorage.getItem('roadops_user_role') || 'CITIZEN';
let currentView = 'dashboard';
let currentIssuePage = 1;
const issuePageSize = 10;
let activeIssueId = null;

// Map & Chart Instances
let publicMap = null;
let publicClusterGroup = null;
let heatmapMap = null;
let heatmapLayer = null;

let chartInstances = {};

// ================= INITIALIZATION =================
document.addEventListener('DOMContentLoaded', () => {
    initClock();
    initAuthUI();
    initNavigation();
    initViews();
    initActionHandlers();
    initDiagnosticModal();
    
    // Auto load current view data
    refreshActiveView();
});

function getAuthHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
    }
    return headers;
}

function initClock() {
    function updateTime() {
        const now = new Date();
        const timeEl = document.getElementById('system-clock');
        if (timeEl) {
            timeEl.textContent = now.toUTCString().replace('GMT', 'UTC');
        }
    }
    updateTime();
    setInterval(updateTime, 1000);
}

// ================= AUTHENTICATION MANAGEMENT =================
function initAuthUI() {
    updateAuthDisplay();

    // Quick Authority Demo Login
    document.getElementById('btn-quick-authority-login')?.addEventListener('click', async () => {
        await quickAuthorityLogin();
    });

    // Token Modal Toggle
    document.getElementById('btn-token-config')?.addEventListener('click', () => {
        const modal = document.getElementById('token-modal');
        const tokenInput = document.getElementById('jwt-token-input');
        if (tokenInput) tokenInput.value = authToken;
        modal.classList.add('active');
    });

    document.getElementById('btn-close-token-modal')?.addEventListener('click', () => {
        document.getElementById('token-modal').classList.remove('active');
    });

    document.getElementById('btn-save-token')?.addEventListener('click', () => {
        const tokenInput = document.getElementById('jwt-token-input');
        authToken = tokenInput.value.trim();
        if (authToken) {
            localStorage.setItem('roadops_auth_token', authToken);
            currentUserRole = 'AUTHORITY';
            localStorage.setItem('roadops_user_role', 'AUTHORITY');
        } else {
            localStorage.removeItem('roadops_auth_token');
            currentUserRole = 'CITIZEN';
        }
        updateAuthDisplay();
        document.getElementById('token-modal').classList.remove('active');
        refreshActiveView();
    });

    document.getElementById('btn-clear-token')?.addEventListener('click', () => {
        authToken = '';
        localStorage.removeItem('roadops_auth_token');
        currentUserRole = 'CITIZEN';
        localStorage.setItem('roadops_user_role', 'CITIZEN');
        updateAuthDisplay();
        document.getElementById('token-modal').classList.remove('active');
        refreshActiveView();
    });
}

function updateAuthDisplay() {
    const dot = document.getElementById('auth-dot');
    const label = document.getElementById('auth-role-label');
    if (authToken) {
        dot.className = 'chip-dot status-online';
        label.textContent = `Role: ${currentUserRole}`;
    } else {
        dot.className = 'chip-dot status-offline';
        label.textContent = 'Public / Citizen';
    }
}

async function quickAuthorityLogin() {
    const email = 'authority_demo@city.gov';
    const password = 'Password@123';
    
    try {
        // Attempt login
        let res = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        if (res.status === 401 || res.status === 404) {
            // Register demo authority account
            await fetch(`${API_BASE_URL}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email,
                    full_name: 'Municipal Authority Inspector',
                    password,
                    role: 'AUTHORITY'
                })
            });

            // Login again
            res = await fetch(`${API_BASE_URL}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
        }

        if (res.ok) {
            const data = await res.json();
            authToken = data.access_token;
            currentUserRole = 'AUTHORITY';
            localStorage.setItem('roadops_auth_token', authToken);
            localStorage.setItem('roadops_user_role', 'AUTHORITY');
            updateAuthDisplay();
            alert('Logged in as Municipal Authority!');
            refreshActiveView();
        } else {
            console.error('Quick login failed:', res.status);
        }
    } catch (err) {
        console.error('Error during quick authority login:', err);
    }
}

// ================= VIEW NAVIGATION =================
function initNavigation() {
    const navTabs = document.querySelectorAll('.nav-tab');
    navTabs.forEach(tab => {
        tab.addEventListener('click', () => {
            navTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            const viewName = tab.getAttribute('data-view');
            switchView(viewName);
        });
    });

    document.getElementById('btn-mobile-menu')?.addEventListener('click', () => {
        document.getElementById('app-sidebar').classList.toggle('open');
    });

    document.getElementById('btn-refresh-all')?.addEventListener('click', () => {
        refreshActiveView();
    });

    document.getElementById('btn-view-all-issues')?.addEventListener('click', () => {
        switchView('issues');
    });
}

function switchView(viewName) {
    currentView = viewName;
    document.querySelectorAll('.view-panel').forEach(panel => {
        panel.classList.remove('active');
    });
    
    // Update sidebar tab active state
    document.querySelectorAll('.nav-tab').forEach(t => {
        t.classList.toggle('active', t.getAttribute('data-view') === viewName);
    });

    const targetPanel = document.getElementById(`view-${viewName}`);
    if (targetPanel) targetPanel.classList.add('active');

    // Close mobile menu if open
    document.getElementById('app-sidebar')?.classList.remove('open');

    refreshActiveView();
}

function refreshActiveView() {
    const syncTag = document.getElementById('last-sync-time');
    if (syncTag) syncTag.textContent = `Synced: ${new Date().toLocaleTimeString()}`;

    if (currentView === 'dashboard') {
        loadDashboardSummary();
    } else if (currentView === 'issues') {
        loadIssuesTable(currentIssuePage);
    } else if (currentView === 'analytics') {
        loadAnalyticsHub();
    } else if (currentView === 'heatmap') {
        loadHeatmapView();
    } else if (currentView === 'public-map') {
        loadPublicMapView();
    }
}

function initViews() {
    // Trend interval toggles
    document.querySelectorAll('#trend-interval-group .btn-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            document.querySelectorAll('#trend-interval-group .btn-chip').forEach(c => c.classList.remove('active'));
            chip.classList.add('active');
            const interval = chip.getAttribute('data-interval');
            const badge = document.getElementById('trend-interval-badge');
            if (badge) badge.textContent = `${interval.toUpperCase()} Aggregation`;
            fetchTrendChartData(interval);
        });
    });

    // Heatmap refresh
    document.getElementById('btn-refresh-heatmap')?.addEventListener('click', () => {
        fetchHeatmapData();
    });

    // Issues filters & search
    document.getElementById('btn-apply-issue-search')?.addEventListener('click', () => {
        currentIssuePage = 1;
        loadIssuesTable(1);
    });

    document.getElementById('issue-search-input')?.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            currentIssuePage = 1;
            loadIssuesTable(1);
        }
    });

    document.getElementById('btn-clear-issue-filters')?.addEventListener('click', () => {
        document.getElementById('issue-search-input').value = '';
        document.getElementById('filter-issue-category').value = '';
        document.getElementById('filter-issue-severity').value = '';
        document.getElementById('filter-issue-status').value = '';
        document.getElementById('filter-issue-priority').value = '';
        document.getElementById('filter-issue-dept').value = '';
        currentIssuePage = 1;
        loadIssuesTable(1);
    });

    // Pagination buttons
    document.getElementById('btn-prev-page')?.addEventListener('click', () => {
        if (currentIssuePage > 1) {
            currentIssuePage--;
            loadIssuesTable(currentIssuePage);
        }
    });

    document.getElementById('btn-next-page')?.addEventListener('click', () => {
        currentIssuePage++;
        loadIssuesTable(currentIssuePage);
    });
}

// ================= VIEW 1: EXECUTIVE DASHBOARD =================
async function loadDashboardSummary() {
    try {
        const res = await fetch(`${API_BASE_URL}/analytics/summary`, {
            headers: getAuthHeaders()
        });

        if (res.status === 401 || res.status === 403) {
            console.warn('Authority role required for analytics summary.');
            // Fallback public fetch for public metrics
            fetchPublicCounts();
            return;
        }

        if (res.ok) {
            const data = await res.json();
            // Populate KPI values
            document.getElementById('kpi-total-reports').textContent = data.total_reports;
            document.getElementById('kpi-active-issues').textContent = data.active_issues;
            document.getElementById('kpi-critical-issues').textContent = data.critical_issues;
            document.getElementById('kpi-high-priority').textContent = data.high_priority_issues;
            document.getElementById('kpi-awaiting-verification').textContent = data.awaiting_verification;
            document.getElementById('kpi-in-progress').textContent = data.in_progress_issues;
            document.getElementById('kpi-fixed-issues').textContent = data.fixed_issues;
            document.getElementById('kpi-closed-issues').textContent = data.closed_issues;

            // Sidebar mini counts
            document.getElementById('side-active-count').textContent = data.active_issues;
            document.getElementById('side-critical-count').textContent = data.critical_issues;

            // Resolution times
            document.getElementById('kpi-res-fixed-hours').textContent = 
                data.avg_resolution_time_hours !== null ? data.avg_resolution_time_hours : '--';
            document.getElementById('kpi-res-closed-hours').textContent = 
                data.avg_close_time_hours !== null ? data.avg_close_time_hours : '--';
        }

        // Load urgent critical issues & mini charts
        loadUrgentIssues();
        loadDashboardMiniCharts();
    } catch (err) {
        console.error('Error loading dashboard summary:', err);
    }
}

async function fetchPublicCounts() {
    try {
        const res = await fetch(`${API_BASE_URL}/reports/map`);
        if (res.ok) {
            const data = await res.json();
            document.getElementById('kpi-total-reports').textContent = data.length;
            document.getElementById('kpi-active-issues').textContent = data.length;
            const crit = data.filter(r => r.severity === 'CRITICAL').length;
            document.getElementById('kpi-critical-issues').textContent = crit;
        }
    } catch (e) {
        console.error(e);
    }
}

async function loadUrgentIssues() {
    const listEl = document.getElementById('urgent-issues-list');
    if (!listEl) return;

    try {
        const res = await fetch(`${API_BASE_URL}/issues?severity=CRITICAL&page_size=5`, {
            headers: getAuthHeaders()
        });

        if (res.ok) {
            const data = await res.json();
            if (data.items.length === 0) {
                listEl.innerHTML = '<div class="text-sm text-secondary p-3">No critical hazards currently open. Great job!</div>';
                return;
            }

            listEl.innerHTML = data.items.map(iss => `
                <div class="urgent-item" onclick="openIssueModal('${iss.id}')">
                    <div class="urgent-left">
                        <span style="font-size: 1.2rem;">${CATEGORY_ICONS[iss.category] || '⚠️'}</span>
                        <div>
                            <div class="urgent-title">${escapeHtml(iss.title)}</div>
                            <div class="urgent-meta">${iss.address || 'Location Coordinates: ' + iss.latitude.toFixed(3) + ', ' + iss.longitude.toFixed(3)}</div>
                        </div>
                    </div>
                    <div>
                        <span class="badge badge-critical">Score: ${iss.priority_score.toFixed(1)}</span>
                    </div>
                </div>
            `).join('');
        }
    } catch (err) {
        listEl.innerHTML = '<div class="text-xs text-muted p-2">Urgent hazard stream unavailable.</div>';
    }
}

async function loadDashboardMiniCharts() {
    try {
        const [catRes, sevRes, statRes] = await Promise.all([
            fetch(`${API_BASE_URL}/analytics/categories`, { headers: getAuthHeaders() }),
            fetch(`${API_BASE_URL}/analytics/severity`, { headers: getAuthHeaders() }),
            fetch(`${API_BASE_URL}/analytics/status`, { headers: getAuthHeaders() }),
        ]);

        if (catRes.ok) {
            const catData = await catRes.json();
            renderMiniCategoryChart(catData.categories);
        }
        if (sevRes.ok) {
            const sevData = await sevRes.json();
            renderMiniSeverityChart(sevData.severities);
        }
        if (statRes.ok) {
            const statData = await statRes.json();
            renderMiniStatusChart(statData.statuses);
        }
    } catch (err) {
        console.error('Error rendering dashboard mini charts:', err);
    }
}

function renderMiniCategoryChart(categories) {
    const ctx = document.getElementById('dashCategoryChart');
    if (!ctx) return;

    if (chartInstances['dashCat']) chartInstances['dashCat'].destroy();

    const topCats = categories.filter(c => c.count > 0).slice(0, 6);
    chartInstances['dashCat'] = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: topCats.map(c => CATEGORY_NAMES[c.category] || c.category),
            datasets: [{
                data: topCats.map(c => c.count),
                backgroundColor: ['#3b82f6', '#ef4444', '#f59e0b', '#10b981', '#a855f7', '#06b6d4'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right', labels: { color: '#94a3b8', boxWidth: 10, font: { size: 10 } } }
            }
        }
    });
}

function renderMiniSeverityChart(severities) {
    const ctx = document.getElementById('dashSeverityChart');
    if (!ctx) return;

    if (chartInstances['dashSev']) chartInstances['dashSev'].destroy();

    chartInstances['dashSev'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: severities.map(s => s.severity),
            datasets: [{
                data: severities.map(s => s.count),
                backgroundColor: ['#ef4444', '#f97316', '#f59e0b', '#10b981'],
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { color: '#94a3b8', font: { size: 10 } }, grid: { display: false } },
                y: { ticks: { color: '#94a3b8', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.05)' } }
            }
        }
    });
}

function renderMiniStatusChart(statuses) {
    const ctx = document.getElementById('dashStatusChart');
    if (!ctx) return;

    if (chartInstances['dashStat']) chartInstances['dashStat'].destroy();

    chartInstances['dashStat'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: statuses.map(s => s.status),
            datasets: [{
                data: statuses.map(s => s.count),
                backgroundColor: '#60a5fa',
                borderRadius: 4
            }]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { color: '#94a3b8', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { ticks: { color: '#94a3b8', font: { size: 9 } }, grid: { display: false } }
            }
        }
    });
}

// ================= VIEW 2: ISSUE COMMAND CENTER =================
async function loadIssuesTable(page = 1) {
    const tbody = document.getElementById('issues-table-body');
    if (!tbody) return;

    tbody.innerHTML = '<tr><td colspan="9" class="text-center py-4 text-muted">Fetching issues...</td></tr>';

    const search = document.getElementById('issue-search-input')?.value || '';
    const category = document.getElementById('filter-issue-category')?.value || '';
    const severity = document.getElementById('filter-issue-severity')?.value || '';
    const status = document.getElementById('filter-issue-status')?.value || '';
    const priority = document.getElementById('filter-issue-priority')?.value || '';
    const dept = document.getElementById('filter-issue-dept')?.value || '';

    const params = new URLSearchParams({
        page: page.toString(),
        page_size: issuePageSize.toString()
    });

    if (search) params.append('search', search);
    if (category) params.append('category', category);
    if (severity) params.append('severity', severity);
    if (status) params.append('status', status);
    if (priority) params.append('priority_level', priority);
    if (dept) params.append('department', dept);

    try {
        const res = await fetch(`${API_BASE_URL}/issues?${params.toString()}`, {
            headers: getAuthHeaders()
        });

        if (!res.ok) {
            tbody.innerHTML = '<tr><td colspan="9" class="text-center py-4 text-muted">Failed to load issues. Please check permissions or login.</td></tr>';
            return;
        }

        const data = await res.json();
        renderIssuesTableRows(data.items);
        updatePagination(data.metadata);
    } catch (err) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center py-4 text-critical">Error loading issues.</td></tr>';
    }
}

function renderIssuesTableRows(issues) {
    const tbody = document.getElementById('issues-table-body');
    if (!issues || issues.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center py-4 text-muted">No matching road issues found.</td></tr>';
        return;
    }

    tbody.innerHTML = issues.map(iss => {
        const sevClass = `badge-${(iss.severity || 'low').toLowerCase()}`;
        const priorityClass = `badge-${(iss.priority_level || 'low').toLowerCase()}`;
        const createdDate = new Date(iss.created_at).toLocaleDateString();

        return `
            <tr>
                <td>
                    <span class="badge ${priorityClass}">
                        ${iss.priority_level} (${iss.priority_score.toFixed(1)})
                    </span>
                </td>
                <td>
                    <div style="font-weight: 600; display: flex; align-items: center; gap: 6px;">
                        <span>${CATEGORY_ICONS[iss.category] || '📌'}</span>
                        <span>${escapeHtml(iss.title)}</span>
                    </div>
                </td>
                <td>
                    <span class="badge ${sevClass}">${iss.severity}</span>
                </td>
                <td>
                    <span class="status-badge-pill status-${iss.status}">${iss.status}</span>
                </td>
                <td>
                    <span class="text-sm text-secondary">${DEPARTMENT_NAMES[iss.assigned_department] || iss.assigned_department || 'Unassigned'}</span>
                </td>
                <td class="text-center font-bold">
                    ${iss.report_count}
                </td>
                <td class="text-xs text-muted" style="max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                    ${escapeHtml(iss.address || `${iss.latitude.toFixed(4)}, ${iss.longitude.toFixed(4)}`)}
                </td>
                <td class="text-xs text-muted">
                    ${createdDate}
                </td>
                <td>
                    <button class="btn btn-sm btn-outline" onclick="openIssueModal('${iss.id}')">
                        Inspect →
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

function updatePagination(meta) {
    const infoEl = document.getElementById('pagination-info');
    const pageNumEl = document.getElementById('current-page-num');
    const prevBtn = document.getElementById('btn-prev-page');
    const nextBtn = document.getElementById('btn-next-page');

    if (infoEl) infoEl.textContent = `Showing Page ${meta.page} of ${meta.pages} (${meta.total} Total Issues)`;
    if (pageNumEl) pageNumEl.textContent = meta.page;
    if (prevBtn) prevBtn.disabled = meta.page <= 1;
    if (nextBtn) nextBtn.disabled = meta.page >= meta.pages;
}

// ================= VIEW 3: ANALYTICS & TRENDS HUB =================
async function loadAnalyticsHub() {
    fetchTrendChartData('day');
    loadDetailedBreakdowns();
    loadGeographicHotspots();
}

async function fetchTrendChartData(interval = 'day') {
    try {
        const res = await fetch(`${API_BASE_URL}/analytics/trends?interval=${interval}&days_back=30`, {
            headers: getAuthHeaders()
        });

        if (!res.ok) return;
        const data = await res.json();
        renderTrendLineChart(data.data);
    } catch (err) {
        console.error('Error loading trends:', err);
    }
}

function renderTrendLineChart(dataPoints) {
    const ctx = document.getElementById('trendTimeChart');
    if (!ctx) return;

    if (chartInstances['trendChart']) chartInstances['trendChart'].destroy();

    const labels = dataPoints.map(p => p.period);
    const countData = dataPoints.map(p => p.count);
    const critData = dataPoints.map(p => p.critical_count);
    const resData = dataPoints.map(p => p.resolved_count);

    chartInstances['trendChart'] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [
                {
                    label: 'Total Issues Reported',
                    data: countData,
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    fill: true,
                    tension: 0.3
                },
                {
                    label: 'Critical Hazards',
                    data: critData,
                    borderColor: '#ef4444',
                    backgroundColor: 'transparent',
                    borderDash: [5, 5],
                    tension: 0.3
                },
                {
                    label: 'Resolved / Closed',
                    data: resData,
                    borderColor: '#10b981',
                    backgroundColor: 'transparent',
                    tension: 0.3
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { labels: { color: '#94a3b8' } }
            },
            scales: {
                x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } }
            }
        }
    });
}

async function loadDetailedBreakdowns() {
    try {
        const [catRes, sevRes] = await Promise.all([
            fetch(`${API_BASE_URL}/analytics/categories`, { headers: getAuthHeaders() }),
            fetch(`${API_BASE_URL}/analytics/severity`, { headers: getAuthHeaders() })
        ]);

        if (catRes.ok) {
            const catData = await catRes.json();
            renderCategoryDetailChart(catData.categories);
        }
        if (sevRes.ok) {
            const sevData = await sevRes.json();
            renderSeverityDetailChart(sevData.severities);
        }
    } catch (e) {
        console.error(e);
    }
}

function renderCategoryDetailChart(categories) {
    const ctx = document.getElementById('categoryDetailChart');
    if (!ctx) return;

    if (chartInstances['catDetail']) chartInstances['catDetail'].destroy();

    chartInstances['catDetail'] = new Chart(ctx, {
        type: 'polarArea',
        data: {
            labels: categories.map(c => CATEGORY_NAMES[c.category] || c.category),
            datasets: [{
                data: categories.map(c => c.count),
                backgroundColor: [
                    'rgba(59, 130, 246, 0.7)',
                    'rgba(239, 68, 68, 0.7)',
                    'rgba(245, 158, 11, 0.7)',
                    'rgba(16, 185, 129, 0.7)',
                    'rgba(168, 85, 247, 0.7)',
                    'rgba(6, 182, 212, 0.7)',
                    'rgba(249, 115, 22, 0.7)',
                    'rgba(100, 116, 139, 0.7)'
                ]
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: { r: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { display: false } } }
        }
    });

    const listEl = document.getElementById('category-breakdown-list');
    if (listEl) {
        listEl.innerHTML = `
            <div style="margin-top: 1rem; display: flex; flex-direction: column; gap: 4px; font-size: 0.78rem;">
                ${categories.map(c => `
                    <div style="display: flex; justify-content: space-between; padding: 3px 0; border-bottom: 1px solid rgba(255,255,255,0.03);">
                        <span>${CATEGORY_ICONS[c.category] || '📌'} ${CATEGORY_NAMES[c.category] || c.category}</span>
                        <span class="font-bold">${c.count} (${c.percentage}%)</span>
                    </div>
                `).join('')}
            </div>
        `;
    }
}

function renderSeverityDetailChart(severities) {
    const ctx = document.getElementById('severityDetailChart');
    if (!ctx) return;

    if (chartInstances['sevDetail']) chartInstances['sevDetail'].destroy();

    chartInstances['sevDetail'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: severities.map(s => s.severity),
            datasets: [{
                data: severities.map(s => s.count),
                backgroundColor: ['#ef4444', '#f97316', '#f59e0b', '#10b981']
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                x: { ticks: { color: '#94a3b8' }, grid: { display: false } },
                y: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } }
            }
        }
    });
}

async function loadGeographicHotspots() {
    const container = document.getElementById('hotspots-container');
    if (!container) return;

    try {
        const res = await fetch(`${API_BASE_URL}/analytics/geographic?grid_size=0.02`, {
            headers: getAuthHeaders()
        });

        if (!res.ok) {
            container.innerHTML = '<div class="text-sm text-secondary p-3">Authority permissions required for hotspot data.</div>';
            return;
        }

        const data = await res.json();
        if (data.clusters.length === 0) {
            container.innerHTML = '<div class="text-sm text-secondary p-3">No active geographic clusters detected.</div>';
            return;
        }

        container.innerHTML = data.clusters.slice(0, 6).map(cl => `
            <div class="hotspot-card">
                <div class="hotspot-info">
                    <h4>${escapeHtml(cl.sample_address || `Coordinates Bin: ${cl.latitude}, ${cl.longitude}`)}</h4>
                    <p>Density: <strong>${cl.density_level}</strong> | Critical Hazards: <strong>${cl.critical_count}</strong></p>
                </div>
                <div class="hotspot-badge">
                    <span class="badge ${cl.density_level === 'HIGH' ? 'badge-critical' : 'badge-medium'}">
                        ${cl.issue_count} Issues
                    </span>
                </div>
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = '<div class="text-xs text-muted p-2">Hotspots calculation failed.</div>';
    }
}

// ================= VIEW 4: GEOGRAPHIC HEATMAP =================
function loadHeatmapView() {
    if (!heatmapMap) {
        heatmapMap = L.map('heatmap-canvas', {
            zoomControl: true,
            attributionControl: true
        }).setView([12.9716, 77.5946], 12);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; OpenStreetMap'
        }).addTo(heatmapMap);
    } else {
        setTimeout(() => heatmapMap.invalidateSize(), 100);
    }

    fetchHeatmapData();
}

async function fetchHeatmapData() {
    const category = document.getElementById('heatmap-filter-category')?.value || '';
    const severity = document.getElementById('heatmap-filter-severity')?.value || '';

    const params = new URLSearchParams();
    if (category) params.append('category', category);
    if (severity) params.append('severity', severity);

    try {
        const res = await fetch(`${API_BASE_URL}/analytics/heatmap?${params.toString()}`, {
            headers: getAuthHeaders()
        });

        if (!res.ok) {
            console.warn('Authority role needed for heatmap endpoint.');
            return;
        }

        const data = await res.json();
        renderHeatmapLayer(data.points);
    } catch (err) {
        console.error('Error fetching heatmap points:', err);
    }
}

function renderHeatmapLayer(points) {
    if (!heatmapMap) return;

    if (heatmapLayer) {
        heatmapMap.removeLayer(heatmapLayer);
    }

    if (!points || points.length === 0) return;

    // Convert to Leaflet Heat format: [lat, lng, intensity]
    const heatPoints = points.map(p => [p.latitude, p.longitude, p.intensity || 0.5]);

    if (typeof L.heatLayer === 'function') {
        heatmapLayer = L.heatLayer(heatPoints, {
            radius: 28,
            blur: 18,
            maxZoom: 17,
            max: 1.0,
            gradient: {
                0.2: '#3b82f6',
                0.4: '#10b981',
                0.6: '#f59e0b',
                0.8: '#f97316',
                1.0: '#ef4444'
            }
        }).addTo(heatmapMap);
    } else {
        console.warn('L.heatLayer plugin not loaded.');
    }

    // Adjust bounds
    if (points.length > 0) {
        const bounds = points.map(p => [p.latitude, p.longitude]);
        heatmapMap.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
    }
}

// ================= VIEW 5: PUBLIC CITIZEN MAP =================
function loadPublicMapView() {
    if (!publicMap) {
        publicMap = L.map('map', {
            zoomControl: true,
            attributionControl: true
        }).setView([12.9716, 77.5946], 12);

        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            maxZoom: 19,
            attribution: '&copy; OpenStreetMap'
        }).addTo(publicMap);

        publicClusterGroup = L.markerClusterGroup();
        publicMap.addLayer(publicClusterGroup);
    } else {
        setTimeout(() => publicMap.invalidateSize(), 100);
    }

    fetchPublicMapPoints();
}

async function fetchPublicMapPoints() {
    try {
        const res = await fetch(`${API_BASE_URL}/reports/map`);
        if (!res.ok) return;

        const reports = await res.json();
        const countEl = document.getElementById('public-active-count');
        if (countEl) countEl.textContent = reports.length;

        publicClusterGroup.clearLayers();
        reports.forEach(r => {
            const marker = L.marker([r.latitude, r.longitude]);
            marker.bindPopup(`
                <div style="font-family: inherit; font-size: 0.85rem;">
                    <strong>${escapeHtml(r.title)}</strong><br>
                    <span>${CATEGORY_NAMES[r.category] || r.category}</span><br>
                    <span style="color: #60a5fa;">Status: ${r.status}</span>
                </div>
            `);
            publicClusterGroup.addLayer(marker);
        });

        if (reports.length > 0) {
            const bounds = reports.map(r => [r.latitude, r.longitude]);
            publicMap.fitBounds(bounds, { padding: [30, 30], maxZoom: 15 });
        }
    } catch (e) {
        console.error(e);
    }
}

// ================= ISSUE INSPECTION DRAWER & ACTIONS =================
async function openIssueModal(issueId) {
    activeIssueId = issueId;
    const modal = document.getElementById('issue-detail-modal');
    modal.classList.add('active');

    try {
        const res = await fetch(`${API_BASE_URL}/issues/${issueId}`, {
            headers: getAuthHeaders()
        });

        if (!res.ok) {
            alert('Failed to load issue details. Check permissions.');
            return;
        }

        const data = await res.json();
        populateIssueModalDetails(data);
    } catch (err) {
        console.error('Error fetching issue detail:', err);
    }
}

function populateIssueModalDetails(issue) {
    document.getElementById('modal-issue-title').textContent = issue.title;
    document.getElementById('modal-category-badge').textContent = issue.category;
    document.getElementById('modal-status-badge').textContent = issue.status;
    document.getElementById('modal-status-badge').className = `meta-val status-badge-pill status-${issue.status}`;
    document.getElementById('modal-severity-badge').textContent = issue.severity;
    document.getElementById('modal-priority-score').textContent = `${issue.priority_score.toFixed(1)} / 100 (${issue.priority_level})`;
    document.getElementById('modal-department-badge').textContent = DEPARTMENT_NAMES[issue.assigned_department] || issue.assigned_department || 'Unassigned';

    document.getElementById('modal-issue-desc').textContent = issue.description || 'No extended description provided.';
    document.getElementById('modal-issue-address').textContent = issue.address || 'Address unrecorded';
    document.getElementById('modal-issue-coords').textContent = `${issue.latitude.toFixed(5)}, ${issue.longitude.toFixed(5)}`;
    document.getElementById('modal-report-count').textContent = issue.reports?.length || 1;

    // Priority Breakdown Bars
    const barsContainer = document.getElementById('modal-priority-bars');
    if (barsContainer && issue.priority_breakdown) {
        const bd = issue.priority_breakdown;
        barsContainer.innerHTML = `
            <div class="breakdown-row">
                <span>Severity Factor:</span>
                <div class="breakdown-bar-bg"><div class="breakdown-bar-fill" style="width: ${(bd.severity_score / 40) * 100}%"></div></div>
                <span>${bd.severity_score.toFixed(1)} pts</span>
            </div>
            <div class="breakdown-row">
                <span>Citizen Reports:</span>
                <div class="breakdown-bar-bg"><div class="breakdown-bar-fill" style="width: ${(bd.report_count_score / 25) * 100}%"></div></div>
                <span>${bd.report_count_score.toFixed(1)} pts</span>
            </div>
            <div class="breakdown-row">
                <span>Traffic / Zone:</span>
                <div class="breakdown-bar-bg"><div class="breakdown-bar-fill" style="width: ${((bd.traffic_density_score + bd.location_zone_score) / 25) * 100}%"></div></div>
                <span>${(bd.traffic_density_score + bd.location_zone_score).toFixed(1)} pts</span>
            </div>
            <div class="breakdown-row">
                <span>Aging (${bd.aging_days.toFixed(1)} days):</span>
                <div class="breakdown-bar-bg"><div class="breakdown-bar-fill" style="width: ${(bd.aging_score / 15) * 100}%"></div></div>
                <span>${bd.aging_score.toFixed(1)} pts</span>
            </div>
        `;
    }

    // Contributing reports
    const reportsList = document.getElementById('modal-reports-list');
    if (reportsList) {
        reportsList.innerHTML = (issue.reports || []).map(r => `
            <div class="report-item-mini">
                <div>
                    <strong>${escapeHtml(r.title)}</strong>
                    <div class="text-xs text-muted">${new Date(r.created_at).toLocaleString()}</div>
                </div>
                <div>
                    <span class="badge badge-sm badge-info">${r.image_count} Photos</span>
                </div>
            </div>
        `).join('');
    }

    // Photos Gallery
    const photoGallery = document.getElementById('modal-photos-gallery');
    if (photoGallery) {
        loadIssuePhotos(issue.id, photoGallery);
    }

    // Status Timeline
    const timelineContainer = document.getElementById('modal-status-timeline');
    if (timelineContainer && issue.status_history) {
        timelineContainer.innerHTML = issue.status_history.map(h => `
            <div class="timeline-entry">
                <div class="timeline-time">${new Date(h.created_at).toLocaleString()}</div>
                <div class="timeline-desc">
                    Transitioned to <strong>${h.new_status}</strong>
                </div>
                ${h.comment ? `<div class="timeline-comment">"${escapeHtml(h.comment)}"</div>` : ''}
            </div>
        `).join('');
    }
}

async function loadIssuePhotos(issueId, container) {
    container.innerHTML = '<div class="text-xs text-muted">Loading photos...</div>';
    try {
        const res = await fetch(`${API_BASE_URL}/issues/${issueId}`, { headers: getAuthHeaders() });
        if (res.ok) {
            const data = await res.json();
            // Fetch reports images
            const imagePromises = (data.reports || []).map(r => fetch(`${API_BASE_URL}/reports/${r.id}/images`));
            const imgResponses = await Promise.all(imagePromises);
            
            let allImages = [];
            for (let r of imgResponses) {
                if (r.ok) {
                    const imgs = await r.json();
                    allImages = allImages.concat(imgs);
                }
            }

            if (allImages.length === 0) {
                container.innerHTML = '<div class="text-xs text-muted">No uploaded photos for this issue.</div>';
                return;
            }

            container.innerHTML = allImages.map(img => `
                <img src="${img.file_url}" alt="Report photo" class="gallery-thumb" onclick="window.open('${img.file_url}', '_blank')">
            `).join('');
        }
    } catch (e) {
        container.innerHTML = '<div class="text-xs text-muted">Photos unavailable.</div>';
    }
}

function initActionHandlers() {
    document.getElementById('btn-close-issue-modal')?.addEventListener('click', () => {
        document.getElementById('issue-detail-modal').classList.remove('active');
        activeIssueId = null;
    });

    // Step 1: Verify Issue
    document.getElementById('btn-submit-verify')?.addEventListener('click', async () => {
        if (!activeIssueId) return;
        const dept = document.getElementById('verify-dept-select').value || null;
        const notes = document.getElementById('verify-notes').value || null;

        try {
            const res = await fetch(`${API_BASE_URL}/issues/${activeIssueId}/verify`, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({ department: dept, notes: notes })
            });
            if (res.ok) {
                alert('Issue successfully verified!');
                openIssueModal(activeIssueId);
                loadIssuesTable(currentIssuePage);
            } else {
                const err = await res.json();
                alert(`Verification failed: ${err.detail || 'Check permissions.'}`);
            }
        } catch (e) {
            alert('Operation failed.');
        }
    });

    // Step 2: Assign Department
    document.getElementById('btn-submit-assign')?.addEventListener('click', async () => {
        if (!activeIssueId) return;
        const dept = document.getElementById('assign-dept-select').value;
        const notes = document.getElementById('assign-notes').value || null;

        try {
            const res = await fetch(`${API_BASE_URL}/issues/${activeIssueId}/assign`, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({ department: dept, notes: notes })
            });
            if (res.ok) {
                alert('Issue assigned successfully!');
                openIssueModal(activeIssueId);
                loadIssuesTable(currentIssuePage);
            } else {
                const err = await res.json();
                alert(`Assignment failed: ${err.detail || 'Check permissions.'}`);
            }
        } catch (e) {
            alert('Operation failed.');
        }
    });

    // Step 3: Update Resolution Status
    document.getElementById('btn-submit-status-update')?.addEventListener('click', async () => {
        if (!activeIssueId) return;
        const newStatus = document.getElementById('update-status-select').value;
        const comment = document.getElementById('update-status-comment').value || null;

        try {
            const res = await fetch(`${API_BASE_URL}/issues/${activeIssueId}/status`, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({ status: newStatus, comment: comment })
            });
            if (res.ok) {
                alert(`Status updated to ${newStatus}!`);
                openIssueModal(activeIssueId);
                loadIssuesTable(currentIssuePage);
            } else {
                const err = await res.json();
                alert(`Status update failed: ${err.detail || 'Check state transition rules.'}`);
            }
        } catch (e) {
            alert('Operation failed.');
        }
    });

    // Step 4: Add Comment
    document.getElementById('btn-submit-comment')?.addEventListener('click', async () => {
        if (!activeIssueId) return;
        const comment = document.getElementById('add-comment-input').value.trim();
        if (!comment) return;

        try {
            const res = await fetch(`${API_BASE_URL}/issues/${activeIssueId}/comments`, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({ comment: comment })
            });
            if (res.ok) {
                document.getElementById('add-comment-input').value = '';
                openIssueModal(activeIssueId);
            } else {
                alert('Failed to post comment.');
            }
        } catch (e) {
            alert('Operation failed.');
        }
    });
}

// ================= AI DIAGNOSTIC MODAL =================
function initDiagnosticModal() {
    const modal = document.getElementById('diagnostic-modal');
    const toggleBtn = document.getElementById('btn-toggle-diagnostics');
    const closeBtn = document.getElementById('modal-close-btn');

    toggleBtn?.addEventListener('click', () => modal.classList.add('active'));
    closeBtn?.addEventListener('click', () => modal.classList.remove('active'));

    document.getElementById('btn-check')?.addEventListener('click', async () => {
        const dot = document.getElementById('health-dot');
        const text = document.getElementById('health-status');
        const logs = document.getElementById('logs');

        try {
            const res = await fetch(`${API_BASE_URL}/health/healthz`);
            if (res.ok) {
                dot.className = 'status-dot online';
                text.textContent = 'API & DB Online (Healthy)';
                logs.innerHTML += `<div class="log-line success">[${new Date().toLocaleTimeString()}] Health Check OK: Database connected.</div>`;
            } else {
                dot.className = 'status-dot offline';
                text.textContent = 'API Error';
                logs.innerHTML += `<div class="log-line error">[${new Date().toLocaleTimeString()}] Health Check Failed.</div>`;
            }
        } catch (e) {
            dot.className = 'status-dot offline';
            text.textContent = 'Connection Failed';
        }
    });

    // Vision Classifier Demo
    document.getElementById('btn-classify-demo')?.addEventListener('click', async () => {
        const fileInput = document.getElementById('ai-demo-file');
        const resBox = document.getElementById('ai-classification-result');
        if (!fileInput.files || fileInput.files.length === 0) {
            alert('Please select an image first.');
            return;
        }

        const formData = new FormData();
        formData.append('file', fileInput.files[0]);

        try {
            const res = await fetch(`${API_BASE_URL}/reports/classify`, {
                method: 'POST',
                body: formData
            });

            if (res.ok) {
                const data = await res.json();
                resBox.style.display = 'block';
                document.getElementById('ai-pred-badge').textContent = `Predicted: ${data.predicted_category} (${(data.confidence * 100).toFixed(1)}% Confidence)`;
                document.getElementById('ai-confidence-bar').style.width = `${(data.confidence * 100).toFixed(1)}%`;
                
                const probs = Object.entries(data.probabilities || {})
                    .map(([k, v]) => `${k}: ${(v * 100).toFixed(1)}%`)
                    .join(' | ');
                document.getElementById('ai-prob-breakdown').textContent = probs;
            }
        } catch (e) {
            alert('Classification request failed.');
        }
    });
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}
