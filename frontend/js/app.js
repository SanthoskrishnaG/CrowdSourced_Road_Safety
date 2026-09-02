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
    } else if (currentView === 'road-health') {
        loadRoadHealthView();
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
    loadWeatherCorrelationAnalytics();
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

    // Phase 14: 9-Factor Priority Breakdown & Explainability
    const barsContainer = document.getElementById('modal-priority-bars');
    if (barsContainer && issue.priority_breakdown) {
        const bd = issue.priority_breakdown;
        const factors = bd.factors || [
            { factor_name: 'Severity', earned_points: bd.severity_score, max_points: 25.0, percentage: (bd.severity_score / 25.0) * 100 },
            { factor_name: 'Independent Reports', earned_points: bd.report_count_score, max_points: 15.0, percentage: (bd.report_count_score / 15.0) * 100 },
            { factor_name: 'Road Health Degradation', earned_points: bd.road_health_score || 0.0, max_points: 15.0, percentage: ((bd.road_health_score || 0) / 15.0) * 100 },
            { factor_name: 'Traffic Importance', earned_points: bd.traffic_density_score, max_points: 10.0, percentage: (bd.traffic_density_score / 10.0) * 100 },
            { factor_name: 'Location Zone', earned_points: bd.location_zone_score, max_points: 10.0, percentage: (bd.location_zone_score / 10.0) * 100 },
            { factor_name: 'Time Unresolved (Aging)', earned_points: bd.aging_score, max_points: 10.0, percentage: (bd.aging_score / 10.0) * 100 },
            { factor_name: 'Predicted ML Risk', earned_points: bd.predicted_risk_score || 0.0, max_points: 10.0, percentage: ((bd.predicted_risk_score || 0) / 10.0) * 100 },
            { factor_name: 'Weather Conditions', earned_points: bd.weather_condition_score || 0.0, max_points: 5.0, percentage: ((bd.weather_condition_score || 0) / 5.0) * 100 },
            { factor_name: 'Citizen Confirmations', earned_points: bd.citizen_confirmations_score || 0.0, max_points: 5.0, percentage: ((bd.citizen_confirmations_score || 0) / 5.0) * 100 },
        ];

        let html = `
            <div class="priority-header-flex">
                <span class="text-xs text-muted">9-Factor Normalized Priority (0–100)</span>
                <button class="btn-recalc-priority" onclick="recalculateActiveIssuePriority('${issue.id}')">
                    🔄 Recalculate Score
                </button>
            </div>
            <div class="priority-9factor-list">
        `;

        factors.forEach(f => {
            const pct = Math.min(100, Math.max(0, f.percentage || (f.earned_points / f.max_points * 100)));
            html += `
                <div class="p-factor-row">
                    <span class="p-factor-name">${escapeHtml(f.factor_name)}</span>
                    <div class="p-factor-bar-track">
                        <div class="p-factor-bar-fill" style="width: ${pct}%;"></div>
                    </div>
                    <span class="p-factor-pts">${f.earned_points.toFixed(1)} / ${f.max_points.toFixed(0)}</span>
                </div>
            `;
        });
        html += '</div>';

        if (bd.top_contributing_drivers && bd.top_contributing_drivers.length > 0) {
            html += `
                <div class="top-drivers-container">
                    <div class="top-drivers-title">Top Score Drivers:</div>
                    <div>
                        ${bd.top_contributing_drivers.map(d => `<span class="top-driver-chip">⚡ ${escapeHtml(d)}</span>`).join('')}
                    </div>
                </div>
            `;
        }

        // Priority History Container
        html += `
            <div class="priority-history-drawer">
                <div class="top-drivers-title">📜 Priority Audit History:</div>
                <div id="priority-history-items-list" class="text-xs text-muted">Loading audit history...</div>
            </div>
        `;

        barsContainer.innerHTML = html;
        loadIssuePriorityHistory(issue.id);
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
    // Photos Gallery
    const photoGallery = document.getElementById('modal-photos-gallery');
    if (photoGallery) {
        loadIssuePhotos(issue.id, photoGallery);
    }

    // Intelligence Metrics & SLA
    if (issue.road_health) {
        document.getElementById('modal-road-health-val').textContent = `${issue.road_health.health_score.toFixed(1)} / 100`;
        document.getElementById('modal-road-health-status').textContent = `Segment Condition: ${issue.road_health.health_status}`;
    }

    if (issue.risk_prediction) {
        document.getElementById('modal-accident-risk-val').textContent = `${(issue.risk_prediction.risk_probability * 100).toFixed(0)}%`;
        document.getElementById('modal-accident-risk-lvl').textContent = `Incident Risk: ${issue.risk_prediction.risk_level} (${issue.risk_prediction.estimated_traffic_delay_min}m delay)`;
    }

    if (issue.sla) {
        const sla = issue.sla;
        document.getElementById('modal-sla-badge').textContent = `SLA: ${sla.sla_status}`;
        document.getElementById('modal-sla-badge').className = `badge ${sla.sla_status === 'BREACHED' ? 'badge-danger' : (sla.sla_status === 'APPROACHING_BREACH' ? 'badge-warning' : 'badge-success')}`;
        document.getElementById('modal-sla-target').textContent = `SLA Window: ${sla.sla_target_hours}h Target`;
        document.getElementById('modal-sla-remaining').textContent = `Remaining: ${sla.remaining_hours > 0 ? sla.remaining_hours.toFixed(1) + 'h' : '0.0h (Overdue)'}`;
        
        const slaPercent = Math.max(0, Math.min(100, (sla.remaining_hours / sla.sla_target_hours) * 100));
        const slaBar = document.getElementById('modal-sla-bar');
        if (slaBar) {
            slaBar.style.width = `${slaPercent}%`;
            slaBar.className = `sla-bar ${sla.sla_status === 'BREACHED' ? 'bg-red' : (sla.sla_status === 'APPROACHING_BREACH' ? 'bg-amber' : 'bg-blue')}`;
        }

        const alertBox = document.getElementById('modal-escalation-alert');
        if (alertBox) {
            if (sla.is_escalated) {
                alertBox.style.display = 'block';
                alertBox.textContent = `⚠️ ESCALATED: ${sla.escalation_reason || 'SLA breached'}`;
            } else {
                alertBox.style.display = 'none';
            }
        }
    }

    // Citizen Re-Verification Box (Visible on FIXED)
    const reverifyBox = document.getElementById('modal-citizen-reverify-box');
    if (reverifyBox) {
        reverifyBox.style.display = issue.status === 'FIXED' ? 'block' : 'none';
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

    // Citizen Re-Verification Handlers
    document.getElementById('btn-citizen-confirm-fixed')?.addEventListener('click', async () => {
        if (!activeIssueId) return;
        const feedback = document.getElementById('reverify-feedback')?.value || 'Satisfied with repair.';
        await submitCitizenVerification(true, feedback, 5);
    });

    document.getElementById('btn-citizen-dispute-reopen')?.addEventListener('click', async () => {
        if (!activeIssueId) return;
        const feedback = document.getElementById('reverify-feedback')?.value || 'Hazard remains dangerous on road.';
        await submitCitizenVerification(false, feedback, 1);
    });

    // Citizen Re-Verification Action
    async function submitCitizenVerification(isVerified, feedbackText, ratingScore) {
        try {
            const res = await fetch(`${API_BASE_URL}/issues/${activeIssueId}/citizen-verify`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...getAuthHeaders()
                },
                body: JSON.stringify({
                    verified: isVerified,
                    feedback: feedbackText,
                    rating: ratingScore
                })
            });

            if (res.ok) {
                const updated = await res.json();
                if (isVerified) {
                    alert(`Thank you! Issue marked CLOSED and citizen verification recorded.`);
                } else {
                    alert(`Issue REOPENED with expedited priority and urgent SLA escalation.`);
                }
                openIssueModal(activeIssueId);
                loadIssuesTable(currentIssuePage);
                fetchExecutiveKPIs();
            } else {
                const err = await res.json();
                alert(`Verification failed: ${err.detail || 'Check status.'}`);
            }
        } catch (e) {
            alert('Network error submitting citizen verification.');
        }
    }

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
            const res = await fetch(`${API_BASE_URL}/reports/classify-image`, {
                method: 'POST',
                headers: authToken ? { 'Authorization': `Bearer ${authToken}` } : {},
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

// ================= WORK ORDER PDF DOWNLOAD =================
document.getElementById('btn-download-work-order')?.addEventListener('click', () => {
    if (!activeIssueId) {
        alert('No active issue selected.');
        return;
    }
    const tokenParam = authToken ? `?token=${encodeURIComponent(authToken)}` : '';
    // Download directly from API
    window.open(`${API_BASE_URL}/issues/${activeIssueId}/work-order`, '_blank');
});

// ================= DASHCAM EDGE ML CONTROLLER =================
function initDashcamController() {
    const runBtn = document.getElementById('btn-run-dashcam-analysis');
    const demoBtn = document.getElementById('btn-demo-dashcam-stream');
    const fileInput = document.getElementById('dashcam-file-input');

    runBtn?.addEventListener('click', async () => {
        const file = fileInput?.files?.[0];
        await processDashcamAnalysis(file);
    });

    demoBtn?.addEventListener('click', async () => {
        await processDashcamAnalysis(null, true);
    });
}

async function processDashcamAnalysis(file, isDemo = false) {
    const listEl = document.getElementById('dashcam-detections-list');
    const countEl = document.getElementById('dashcam-detection-count');
    const chipsEl = document.getElementById('dashcam-summary-chips');

    listEl.innerHTML = '<div class="text-center p-4"><span class="pulse-dot"></span> Running Edge ML Vision Inference on Video Frames...</div>';

    const formData = new FormData();
    if (file) {
        formData.append('video_file', file);
    } else {
        // Create dummy video blob for demonstration
        const dummyBlob = new Blob(['simulated-dashcam-stream-bytes'], { type: 'video/mp4' });
        formData.append('video_file', dummyBlob, 'dashcam_patrol_stream.mp4');
    }

    formData.append('duration_sec', document.getElementById('dashcam-duration')?.value || '10');
    formData.append('sample_interval_sec', document.getElementById('dashcam-interval')?.value || '1.0');

    const startCoords = document.getElementById('dashcam-start-coords')?.value?.split(',') || ['12.9716', '77.5946'];
    const endCoords = document.getElementById('dashcam-end-coords')?.value?.split(',') || ['12.9780', '77.6020'];

    formData.append('start_lat', parseFloat(startCoords[0]) || 12.9716);
    formData.append('start_lng', parseFloat(startCoords[1]) || 77.5946);
    formData.append('end_lat', parseFloat(endCoords[0]) || 12.9780);
    formData.append('end_lng', parseFloat(endCoords[1]) || 77.6020);

    try {
        const res = await fetch(`${API_BASE_URL}/stream/analyze`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: formData
        });

        if (!res.ok) {
            listEl.innerHTML = '<div class="alert alert-danger">Dashcam stream analysis failed. Please verify authority credentials.</div>';
            return;
        }

        const data = await res.json();
        countEl.textContent = data.detections_count;

        // Render Summary Chips
        chipsEl.innerHTML = Object.entries(data.summary_by_category || {})
            .map(([cat, cnt]) => `<span class="summary-chip">${cat}: <b>${cnt}</b></span>`)
            .join('');

        if (!data.hazards || data.hazards.length === 0) {
            listEl.innerHTML = '<div class="empty-state-card"><p>No road safety hazards detected in video clip.</p></div>';
            return;
        }

        listEl.innerHTML = data.hazards.map((h, idx) => `
            <div class="dashcam-item-card" id="dashcam-item-${idx}">
                <div class="dashcam-thumb-wrap">
                    <img src="${h.snapshot_base64 || 'https://img.icons8.com/fluency/96/road.png'}" alt="${escapeHtml(h.category)}">
                </div>
                <div class="dashcam-item-info">
                    <div class="dashcam-item-meta">
                        <span class="dashcam-time-tag">⏱️ ${h.timestamp_sec.toFixed(1)}s</span>
                        <span class="badge ${getSeverityBadgeClass(h.severity)}">${h.severity}</span>
                        <span class="badge badge-indigo">${h.category}</span>
                    </div>
                    <div class="text-sm font-bold">${escapeHtml(h.category)} Hazard Detected</div>
                    <div class="text-xs text-muted">
                        Confidence: ${(h.confidence * 100).toFixed(1)}% | Coordinates: ${h.estimated_lat?.toFixed(5)}, ${h.estimated_lng?.toFixed(5)}
                    </div>
                </div>
                <div class="dashcam-item-actions">
                    <button class="btn-convert-report" onclick="convertStreamHazard(${idx}, ${JSON.stringify(h).replace(/"/g, '&quot;')})">
                        + Log Report
                    </button>
                </div>
            </div>
        `).join('');

    } catch (e) {
        listEl.innerHTML = '<div class="alert alert-danger">Network error during stream processing.</div>';
    }
}

// Convert Stream Detection to Civic Report
window.convertStreamHazard = async function(idx, hazardData) {
    const itemCard = document.getElementById(`dashcam-item-${idx}`);
    if (itemCard) itemCard.style.opacity = '0.5';

    try {
        const payload = {
            category: hazardData.category,
            severity: hazardData.severity || 'HIGH',
            title: `Dashcam Detected ${hazardData.category} at ${hazardData.timestamp_sec}s`,
            description: `Automatic hazard detection on live video stream with ${(hazardData.confidence * 100).toFixed(1)}% confidence.`,
            latitude: hazardData.estimated_lat || 12.9716,
            longitude: hazardData.estimated_lng || 77.5946,
            timestamp_sec: hazardData.timestamp_sec,
            snapshot_base64: hazardData.snapshot_base64
        };

        const res = await fetch(`${API_BASE_URL}/stream/convert-to-report`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                ...getAuthHeaders()
            },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            const rep = await res.json();
            alert(`Report #${rep.id.slice(0, 8)} successfully generated and merged with canonical issue #${rep.issue_id?.slice(0, 8) || 'Created'}!`);
            if (itemCard) {
                itemCard.innerHTML = `<div class="p-2 text-green font-bold">✔️ Converted to Report #${rep.id.slice(0, 8)}</div>`;
            }
            fetchIssues();
            fetchExecutiveKPIs();
        } else {
            alert('Failed to convert stream hazard to report.');
            if (itemCard) itemCard.style.opacity = '1';
        }
    } catch (e) {
        alert('Operation failed.');
        if (itemCard) itemCard.style.opacity = '1';
    }
};

// ================= PWA SERVICE WORKER REGISTRATION =================
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('./sw.js')
            .then(reg => console.log('[PWA] ServiceWorker registered with scope:', reg.scope))
            .catch(err => console.warn('[PWA] ServiceWorker registration failed:', err));
    });
}

// Global manual sync trigger for offline queue
window.triggerManualSync = async function() {
    if (typeof syncOfflineDrafts === 'function') {
        const res = await syncOfflineDrafts(API_BASE_URL, getAuthHeaders());
        if (res.synced > 0) {
            alert(`Offline Sync Complete: ${res.synced} draft reports uploaded to server.`);
            fetchIssues();
            fetchExecutiveKPIs();
        }
    }
};

// Initialize Dashcam & Road Health Controllers
document.addEventListener('DOMContentLoaded', () => {
    initDashcamController();
    initRoadHealthController();
});

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ==========================================================================
// PHASE 11 & 12: ROAD HEALTH ENGINE & PREDICTIVE ROAD RISK CONTROLLER
// ==========================================================================

let roadHealthDistChart = null;
let roadHealthTrendsChart = null;

function initRoadHealthController() {
    // Refresh Button
    document.getElementById('btn-refresh-road-health')?.addEventListener('click', () => {
        loadRoadHealthView();
    });

    // Predictive Risk Filters
    document.getElementById('risk-filter-level')?.addEventListener('change', () => fetchRoadRiskPredictions());
    document.getElementById('risk-filter-roadtype')?.addEventListener('change', () => fetchRoadRiskPredictions());
    document.getElementById('risk-filter-sort')?.addEventListener('change', () => fetchRoadRiskPredictions());

    // Diagnostics Modal Close
    document.getElementById('btn-close-road-modal')?.addEventListener('click', closeRoadDiagnosticsModal);
    document.getElementById('modal-road-diagnostics-backdrop')?.addEventListener('click', (e) => {
        if (e.target.id === 'modal-road-diagnostics-backdrop') closeRoadDiagnosticsModal();
    });
}

async function loadRoadHealthView() {
    await Promise.all([
        fetchRoadHealthAnalytics(),
        fetchRoadRiskPredictions(),
    ]);
}

async function fetchRoadHealthAnalytics() {
    try {
        const res = await fetch(`${API_BASE_URL}/analytics/road-health?top_n=8`, {
            headers: getAuthHeaders()
        });

        if (res.status === 401 || res.status === 403) {
            console.warn('Authority privileges required for road health analytics.');
            return;
        }

        if (!res.ok) throw new Error('Failed to load road health analytics');
        const data = await res.json();

        // 1. KPI Ribbon
        const avgScore = data.summary?.average_health_score ?? 100;
        document.getElementById('kpi-road-avg-health').textContent = `${avgScore} / 100`;
        document.getElementById('kpi-road-total-segments').textContent = data.summary?.total_monitored_segments ?? 0;
        document.getElementById('kpi-road-total-km').textContent = `${data.summary?.total_monitored_km ?? 0} km network`;
        document.getElementById('kpi-road-critical-count').textContent = data.summary?.critical_segments_count ?? 0;

        let statusText = 'Network Condition: Excellent';
        if (avgScore < 50) statusText = 'Network Condition: Critical';
        else if (avgScore < 70) statusText = 'Network Condition: Fair / Degraded';
        else if (avgScore < 85) statusText = 'Network Condition: Good';
        document.getElementById('kpi-road-network-status').textContent = statusText;

        // 2. Leaderboards
        renderRoadLeaderboard('worst-roads-table-container', data.worst_roads, true);
        renderRoadLeaderboard('best-roads-table-container', data.best_roads, false);

        // 3. Health Distribution Chart
        renderRoadHealthDistributionChart(data.health_distribution);

        // 4. Health Trends Chart
        renderRoadHealthTrendsChart(data.health_trends);

    } catch (err) {
        console.error('Error in fetchRoadHealthAnalytics:', err);
    }
}

function renderRoadLeaderboard(containerId, roadsList, isWorst) {
    const container = document.getElementById(containerId);
    if (!container) return;

    if (!roadsList || roadsList.length === 0) {
        container.innerHTML = '<div class="empty-state-card"><p>No road corridors registered yet.</p></div>';
        return;
    }

    let html = `
        <table class="road-table">
            <thead>
                <tr>
                    <th>Corridor Name</th>
                    <th>Type</th>
                    <th>Health Score</th>
                    <th>Status</th>
                    <th>Active Issues</th>
                    <th>Action</th>
                </tr>
            </thead>
            <tbody>
    `;

    roadsList.forEach(r => {
        const score = r.health_score;
        let barColor = '#10b981';
        let statusClass = 'status-excellent';
        if (score < 30) { barColor = '#ef4444'; statusClass = 'status-critical'; }
        else if (score < 50) { barColor = '#f97316'; statusClass = 'status-poor'; }
        else if (score < 70) { barColor = '#f59e0b'; statusClass = 'status-fair'; }
        else if (score < 85) { barColor = '#3b82f6'; statusClass = 'status-good'; }

        html += `
            <tr>
                <td>
                    <strong>${escapeHtml(r.name)}</strong>
                    <div class="text-xs text-muted">${r.length_km} km</div>
                </td>
                <td><span class="badge">${r.road_type}</span></td>
                <td>
                    <div class="health-meter-cell">
                        <span class="font-bold">${score}</span>
                        <div class="health-bar-track">
                            <div class="health-bar-fill" style="width: ${score}%; background: ${barColor};"></div>
                        </div>
                    </div>
                </td>
                <td><span class="health-status-badge ${statusClass}">${r.health_status}</span></td>
                <td><span class="font-mono font-bold">${r.active_issues_count}</span></td>
                <td>
                    <button class="btn btn-xs btn-outline" onclick="openRoadDiagnosticsModal('${r.road_id}')">
                        🔍 Inspect
                    </button>
                </td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    container.innerHTML = html;
}

function renderRoadHealthDistributionChart(distribution) {
    const ctx = document.getElementById('roadHealthDistributionChart')?.getContext('2d');
    if (!ctx || !distribution) return;

    if (roadHealthDistChart) roadHealthDistChart.destroy();

    const labels = distribution.map(d => d.status);
    const dataVals = distribution.map(d => d.count);
    const colors = ['#10b981', '#3b82f6', '#f59e0b', '#f97316', '#ef4444'];

    roadHealthDistChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: dataVals,
                backgroundColor: colors,
                borderWidth: 2,
                borderColor: '#0f172a'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'bottom', labels: { color: '#94a3b8', boxWidth: 12 } }
            },
            cutout: '65%'
        }
    });

    // Render Pills
    const pillsContainer = document.getElementById('road-health-dist-pills');
    if (pillsContainer) {
        pillsContainer.innerHTML = distribution.map((d, i) => `
            <div class="health-pill">
                <span class="dot" style="display:inline-block; width:8px; height:8px; border-radius:50%; background:${colors[i]}"></span>
                <span>${d.status}: <strong>${d.count}</strong> (${d.percentage}%)</span>
            </div>
        `).join('');
    }
}

function renderRoadHealthTrendsChart(trends) {
    const ctx = document.getElementById('roadHealthTrendsChart')?.getContext('2d');
    if (!ctx || !trends || trends.length === 0) return;

    if (roadHealthTrendsChart) roadHealthTrendsChart.destroy();

    const labels = trends.map(t => t.period);
    const scores = trends.map(t => t.avg_health_score);

    roadHealthTrendsChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Avg Health Score (0-100)',
                data: scores,
                borderColor: '#6366f1',
                backgroundColor: 'rgba(99, 102, 241, 0.15)',
                tension: 0.35,
                fill: true,
                pointRadius: 4,
                pointBackgroundColor: '#818cf8',
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    min: 0,
                    max: 100,
                    grid: { color: 'rgba(255, 255, 255, 0.05)' },
                    ticks: { color: '#94a3b8' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#94a3b8' }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}

async function fetchRoadRiskPredictions() {
    const grid = document.getElementById('road-risk-cards-grid');
    if (!grid) return;

    const riskLevel = document.getElementById('risk-filter-level')?.value || '';
    const roadType = document.getElementById('risk-filter-roadtype')?.value || '';
    const sortBy = document.getElementById('risk-filter-sort')?.value || 'risk_desc';

    const params = new URLSearchParams();
    if (riskLevel) params.append('risk_level', riskLevel);
    if (roadType) params.append('road_type', roadType);
    if (sortBy) params.append('sort_by', sortBy);

    try {
        const res = await fetch(`${API_BASE_URL}/predictions/road-risk?${params.toString()}`, {
            headers: getAuthHeaders()
        });

        if (res.status === 401 || res.status === 403) return;
        if (!res.ok) throw new Error('Failed to fetch predictions');

        const data = await res.json();
        const highCount = data.summary?.high_or_critical_risk_count ?? 0;
        const highBadge = document.getElementById('kpi-road-high-risk-count');
        if (highBadge) highBadge.textContent = highCount;

        if (!data.predictions || data.predictions.length === 0) {
            grid.innerHTML = '<div class="empty-state-card w-100"><p>No corridors match selected risk filters.</p></div>';
            return;
        }

        grid.innerHTML = data.predictions.map(p => {
            const rLevel = p.risk_level.toLowerCase();
            const probPct = Math.round(p.worsening_probability * 100);

            return `
                <div class="road-risk-card card-risk-${rLevel}">
                    <div>
                        <div class="risk-card-head">
                            <div>
                                <h4 class="risk-card-title">${escapeHtml(p.name)}</h4>
                                <span class="risk-card-meta">${p.road_type} • Importance: ${p.importance}</span>
                            </div>
                            <span class="risk-level-tag risk-${rLevel}">${p.risk_level}</span>
                        </div>

                        <div class="risk-metrics-row">
                            <div class="risk-metric-item">
                                <span class="risk-metric-lbl">Risk Score</span>
                                <span class="risk-metric-val">${p.risk_score} / 100</span>
                            </div>
                            <div class="risk-metric-item">
                                <span class="risk-metric-lbl">Worsening Likelihood</span>
                                <span class="risk-metric-val text-primary-glow">${probPct}%</span>
                            </div>
                        </div>

                        ${p.top_contributing_factor ? `
                            <div class="top-factor-preview">
                                <strong>Top Driver:</strong> ${escapeHtml(p.top_contributing_factor)}
                            </div>
                        ` : ''}
                    </div>

                    <div class="d-flex justify-between align-center mt-2">
                        <span class="text-xs text-muted">Health: ${p.current_health_score}/100</span>
                        <button class="btn btn-xs btn-primary" onclick="openRoadDiagnosticsModal('${p.road_id}')">
                            🔬 Diagnostics
                        </button>
                    </div>
                </div>
            `;
        }).join('');

    } catch (err) {
        console.error('Error in fetchRoadRiskPredictions:', err);
    }
}

window.openRoadDiagnosticsModal = async function(roadId) {
    const modalBackdrop = document.getElementById('modal-road-diagnostics-backdrop');
    const modalBody = document.getElementById('modal-road-body');
    const modalTitle = document.getElementById('modal-road-name');
    const modalType = document.getElementById('modal-road-type-badge');

    if (!modalBackdrop || !modalBody) return;

    modalBody.innerHTML = '<div class="loading-state">Computing multi-factor health and ML risk breakdown...</div>';
    modalBackdrop.classList.add('open');

    try {
        const [healthRes, riskRes] = await Promise.all([
            fetch(`${API_BASE_URL}/roads/${roadId}/health`, { headers: getAuthHeaders() }),
            fetch(`${API_BASE_URL}/roads/${roadId}/risk`, { headers: getAuthHeaders() }),
        ]);

        if (!healthRes.ok || !riskRes.ok) throw new Error('Failed to retrieve road diagnostics');

        const hData = await healthRes.json();
        const rData = await riskRes.json();

        modalTitle.textContent = hData.name;
        modalType.textContent = `${hData.road_type} • ${hData.importance}`;

        const factors = hData.factors || {};
        const metrics = hData.metrics || {};
        const riskFactors = rData.contributing_factors || [];

        modalBody.innerHTML = `
            <div class="diag-grid-2col mb-4">
                <!-- Left: 6 Normalized Health Penalties -->
                <div class="glass-card">
                    <div class="card-head">
                        <h4>🏥 Health Engine Component Penalties</h4>
                        <span class="health-status-badge status-${hData.health_status.toLowerCase()}">${hData.health_score} / 100 (${hData.health_status})</span>
                    </div>

                    <div class="factor-penalty-item">
                        <span>Active Unresolved Issues (${metrics.active_issues_count})</span>
                        <div class="factor-penalty-bar-wrap">
                            <div class="factor-penalty-fill" style="width: ${factors.active_issue_penalty}%;"></div>
                        </div>
                        <span class="font-mono text-xs">${factors.active_issue_penalty}%</span>
                    </div>

                    <div class="factor-penalty-item">
                        <span>Severity Weight (${metrics.critical_issues_count} Critical, ${metrics.high_issues_count} High)</span>
                        <div class="factor-penalty-bar-wrap">
                            <div class="factor-penalty-fill" style="width: ${factors.severity_penalty}%;"></div>
                        </div>
                        <span class="font-mono text-xs">${factors.severity_penalty}%</span>
                    </div>

                    <div class="factor-penalty-item">
                        <span>Corridor Density (${metrics.issues_per_km} / km)</span>
                        <div class="factor-penalty-bar-wrap">
                            <div class="factor-penalty-fill" style="width: ${factors.density_penalty}%;"></div>
                        </div>
                        <span class="font-mono text-xs">${factors.density_penalty}%</span>
                    </div>

                    <div class="factor-penalty-item">
                        <span>Report Velocity (30d Reports)</span>
                        <div class="factor-penalty-bar-wrap">
                            <div class="factor-penalty-fill" style="width: ${factors.report_frequency_penalty}%;"></div>
                        </div>
                        <span class="font-mono text-xs">${factors.report_frequency_penalty}%</span>
                    </div>

                    <div class="factor-penalty-item">
                        <span>Resolution Turnaround (${metrics.avg_resolution_hours ? metrics.avg_resolution_hours + 'h' : 'N/A'})</span>
                        <div class="factor-penalty-bar-wrap">
                            <div class="factor-penalty-fill" style="width: ${factors.resolution_time_penalty}%;"></div>
                        </div>
                        <span class="font-mono text-xs">${factors.resolution_time_penalty}%</span>
                    </div>

                    <div class="factor-penalty-item">
                        <span>Recent Surge (${metrics.recent_7d_reports_count} in past 7d)</span>
                        <div class="factor-penalty-bar-wrap">
                            <div class="factor-penalty-fill" style="width: ${factors.recent_incidents_penalty}%;"></div>
                        </div>
                        <span class="font-mono text-xs">${factors.recent_incidents_penalty}%</span>
                    </div>
                </div>

                <!-- Right: Predictive Risk & Explainability -->
                <div class="glass-card">
                    <div class="card-head">
                        <h4>🔮 ML Deterioration Risk Forecast</h4>
                        <span class="risk-level-tag risk-${rData.risk_level.toLowerCase()}">${rData.risk_score} / 100 (${rData.risk_level})</span>
                    </div>

                    <div class="risk-metrics-row mb-3">
                        <div class="risk-metric-item">
                            <span class="risk-metric-lbl">30-Day Worsening Likelihood</span>
                            <span class="risk-metric-val text-primary-glow">${Math.round(rData.worsening_probability * 100)}%</span>
                        </div>
                        <div class="risk-metric-item">
                            <span class="risk-metric-lbl">Model Version</span>
                            <span class="risk-metric-val text-xs font-mono">${rData.model_version}</span>
                        </div>
                    </div>

                    <h5 class="text-xs text-muted mb-2">PRIMARY EXPLAINABILITY FACTORS:</h5>
                    <div class="explainability-factors-list">
                        ${riskFactors.map(f => `
                            <div class="contributing-factor-box">
                                <div class="factor-head-row">
                                    <span>${escapeHtml(f.factor_name)}</span>
                                    <span class="text-primary-glow">+${f.impact_percentage}%</span>
                                </div>
                                <p class="factor-desc-text">${escapeHtml(f.description)}</p>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>

            <!-- Disclaimer Notice Footer -->
            <div class="disclaimer-alert-card">
                <div class="disclaimer-icon">ℹ️</div>
                <div class="disclaimer-content text-xs">
                    ${rData.disclaimer}
                </div>
            </div>
        `;

    } catch (err) {
        modalBody.innerHTML = `<div class="p-3 text-critical">Failed to load diagnostics: ${err.message}</div>`;
    }
};

function closeRoadDiagnosticsModal() {
    document.getElementById('modal-road-diagnostics-backdrop')?.classList.remove('open');
}

// ==========================================================================
// PHASE 13: WEATHER INTELLIGENCE & CORRELATION DASHBOARD INTEGRATION
// ==========================================================================

async function loadWeatherCorrelationAnalytics() {
    try {
        const [currRes, corrRes] = await Promise.all([
            fetch(`${API_BASE_URL}/weather/current`, { headers: getAuthHeaders() }),
            fetch(`${API_BASE_URL}/analytics/weather-correlations?days=30`, { headers: getAuthHeaders() })
        ]);

        if (currRes.ok) {
            const curr = await currRes.json();
            renderCurrentWeatherTelemetry(curr);
        }

        if (corrRes.ok) {
            const corr = await corrRes.json();
            renderWeatherCorrelationChart(corr);
            renderWeatherCorrelationMetrics(corr);
        }
    } catch (err) {
        console.error('Error loading weather correlation analytics:', err);
    }
}

function renderCurrentWeatherTelemetry(curr) {
    const badgeEl = document.getElementById('weather-provider-badge');
    const stripEl = document.getElementById('weather-current-strip');
    if (!badgeEl || !stripEl) return;

    const isMock = curr.is_mock;
    badgeEl.className = isMock ? 'badge badge-warning' : 'badge badge-success';
    badgeEl.textContent = isMock ? `🟡 Provider: ${curr.provider_name} (Dev / Simulated)` : `🟢 Provider: ${curr.provider_name} (Live Telemetry)`;

    stripEl.innerHTML = `
        <div class="weather-stat-box">
            <span class="weather-stat-lbl">Condition</span>
            <span class="weather-stat-val">🌦️ ${escapeHtml(curr.condition)}</span>
        </div>
        <div class="weather-stat-box">
            <span class="weather-stat-lbl">Temperature</span>
            <span class="weather-stat-val">${curr.temperature_celsius.toFixed(1)}°C</span>
        </div>
        <div class="weather-stat-box">
            <span class="weather-stat-lbl">Humidity</span>
            <span class="weather-stat-val">${curr.humidity_percent.toFixed(0)}%</span>
        </div>
        <div class="weather-stat-box">
            <span class="weather-stat-lbl">Precipitation Rate</span>
            <span class="weather-stat-val">${curr.rainfall_mm_per_hour.toFixed(1)} mm/h</span>
        </div>
        <div class="weather-stat-box">
            <span class="weather-stat-lbl">Severe Event</span>
            <span class="weather-stat-val ${curr.is_severe ? 'text-critical' : 'text-success'}">${curr.is_severe ? '⚠️ ALERT ACTIVE' : '✅ NORMAL'}</span>
        </div>
    `;
}

function renderWeatherCorrelationChart(corrData) {
    const ctx = document.getElementById('weatherCorrelationChart');
    if (!ctx) return;

    if (chartInstances['weatherCorrChart']) chartInstances['weatherCorrChart'].destroy();

    const history = corrData.trend_history || [];
    const labels = history.map(h => h.date);
    const rainData = history.map(h => h.rainfall_mm);
    const floodData = history.map(h => h.flooding_reports_count);
    const potholeData = history.map(h => h.pothole_reports_count);
    const damageData = history.map(h => h.road_damage_reports_count);

    chartInstances['weatherCorrChart'] = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    type: 'bar',
                    label: 'Daily Rainfall (mm)',
                    data: rainData,
                    backgroundColor: 'rgba(59, 130, 246, 0.4)',
                    borderColor: '#3b82f6',
                    borderWidth: 1,
                    yAxisID: 'yRain',
                    order: 3
                },
                {
                    type: 'line',
                    label: 'Flooding Hazards',
                    data: floodData,
                    borderColor: '#06b6d4',
                    backgroundColor: 'transparent',
                    tension: 0.2,
                    yAxisID: 'yReports',
                    order: 1
                },
                {
                    type: 'line',
                    label: 'Pothole Surges (Lagged)',
                    data: potholeData,
                    borderColor: '#f59e0b',
                    backgroundColor: 'transparent',
                    tension: 0.2,
                    yAxisID: 'yReports',
                    order: 2
                },
                {
                    type: 'line',
                    label: 'Road Damage Reports',
                    data: damageData,
                    borderColor: '#ef4444',
                    backgroundColor: 'transparent',
                    borderDash: [4, 4],
                    tension: 0.2,
                    yAxisID: 'yReports',
                    order: 2
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: { mode: 'index', intersect: false },
            plugins: {
                legend: { labels: { color: '#94a3b8' } },
                tooltip: { backgroundColor: 'rgba(15, 23, 42, 0.95)' }
            },
            scales: {
                x: { ticks: { color: '#94a3b8' }, grid: { color: 'rgba(255,255,255,0.05)' } },
                yRain: {
                    type: 'linear',
                    position: 'left',
                    title: { display: true, text: 'Rainfall (mm)', color: '#3b82f6' },
                    ticks: { color: '#3b82f6' },
                    grid: { color: 'rgba(255,255,255,0.05)' }
                },
                yReports: {
                    type: 'linear',
                    position: 'right',
                    title: { display: true, text: 'Hazard Incidents Reported', color: '#94a3b8' },
                    ticks: { color: '#94a3b8', stepSize: 1 },
                    grid: { drawOnChartArea: false }
                }
            }
        }
    });
}

function renderWeatherCorrelationMetrics(corrData) {
    const metricsEl = document.getElementById('weather-correlations-metrics');
    const advisoriesEl = document.getElementById('weather-advisories-list');
    if (!metricsEl) return;

    const correlations = corrData.category_correlations || [];
    metricsEl.innerHTML = correlations.map(c => `
        <div class="correlation-metric-card">
            <div class="corr-card-head">
                <span class="corr-cat-title">${escapeHtml(c.category_label || c.category)}</span>
                <span class="badge ${c.pearson_r > 0.6 ? 'badge-danger' : c.pearson_r > 0.3 ? 'badge-warning' : 'badge-info'}">
                    ${c.correlation_strength}
                </span>
            </div>
            <div class="corr-numbers-row">
                <div class="corr-num-pill">Pearson r: <strong>${c.pearson_r >= 0 ? '+' : ''}${c.pearson_r.toFixed(2)}</strong></div>
                <div class="corr-num-pill">Rain Surge Multiplier: <strong>${c.rainfall_multiplier.toFixed(1)}x</strong></div>
            </div>
            <div class="text-xs text-muted">
                ${c.lag_days_analyzed > 0 ? `⚡ Evaluated with ${c.lag_days_analyzed}-day delayed saturation lag.` : '⚡ Immediate direct rainfall correlation.'}
            </div>
        </div>
    `).join('');

    if (advisoriesEl && corrData.advisory_recommendations) {
        advisoriesEl.innerHTML = `
            <h5 class="text-xs text-primary mb-2 font-bold uppercase tracking-wide">🛡️ Proactive Weather-Hazard Directives:</h5>
            ${corrData.advisory_recommendations.map(adv => `
                <div class="advisory-item">
                    <span>📌</span>
                    <span>${escapeHtml(adv)}</span>
                </div>
            `).join('')}
        `;
    }
}

// ==========================================================================
// PHASE 14: ADVANCED PRIORITY RECALCULATION & AUDIT HISTORY
// ==========================================================================

async function recalculateActiveIssuePriority(issueId) {
    const btn = document.querySelector('.btn-recalc-priority');
    if (btn) {
        btn.textContent = '🔄 Recalculating...';
        btn.disabled = true;
    }

    try {
        const res = await fetch(`${API_BASE_URL}/issues/${issueId}/recalculate-priority`, {
            method: 'POST',
            headers: getAuthHeaders()
        });

        if (!res.ok) {
            alert('Failed to recalculate priority. Ensure you are logged in with authority permissions.');
            return;
        }

        const updatedIssue = await res.json();
        populateIssueModalDetails(updatedIssue);
    } catch (err) {
        console.error('Error recalculating priority:', err);
    } finally {
        if (btn) {
            btn.textContent = '🔄 Recalculate Score';
            btn.disabled = false;
        }
    }
}

async function loadIssuePriorityHistory(issueId) {
    const container = document.getElementById('priority-history-items-list');
    if (!container) return;

    try {
        const res = await fetch(`${API_BASE_URL}/issues/${issueId}/priority-history`, {
            headers: getAuthHeaders()
        });

        if (!res.ok) {
            container.innerHTML = '<div class="text-xs text-muted">Priority audit history unavailable.</div>';
            return;
        }

        const history = await res.json();
        if (history.length === 0) {
            container.innerHTML = '<div class="text-xs text-muted">No historical priority recalculations recorded yet.</div>';
            return;
        }

        container.innerHTML = history.map(h => `
            <div class="priority-history-item">
                <div class="ph-head">
                    <span style="color: #818cf8;">${escapeHtml(h.trigger_event || 'SYSTEM_EVALUATION')}</span>
                    <span>${h.previous_score.toFixed(1)} ➔ ${h.new_score.toFixed(1)} pts (${h.new_level})</span>
                </div>
                <div class="text-xs text-muted">
                    ${new Date(h.created_at).toLocaleString()}
                </div>
            </div>
        `).join('');
    } catch (err) {
        container.innerHTML = '<div class="text-xs text-muted">Failed to fetch priority history.</div>';
    }
}


