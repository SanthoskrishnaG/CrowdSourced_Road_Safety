const API_BASE_URL = 'http://localhost:8000/api/v1';

// Category Emoji Map
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

// Initialize Leaflet Map
let map;
let markerClusterGroup;
let currentReports = [];

function initMap() {
    // Default view: Center on standard view
    map = L.map('map', {
        zoomControl: true,
        attributionControl: true
    }).setView([12.9716, 77.5946], 12);

    // OpenStreetMap Tile Layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    // Initialize Marker Cluster Group
    markerClusterGroup = L.markerClusterGroup({
        showCoverageOnHover: false,
        spiderfyOnMaxZoom: true,
        disableClusteringAtZoom: 17
    });
    map.addLayer(markerClusterGroup);

    // Fetch initial map reports
    fetchMapReports();
}

// Fetch Map Reports from API
async function fetchMapReports() {
    const category = document.getElementById('filter-category').value;
    const severity = document.getElementById('filter-severity').value;
    const status = document.getElementById('filter-status').value;

    const params = new URLSearchParams();
    if (category) params.append('category', category);
    if (severity) params.append('severity', severity);
    if (status) params.append('status', status);

    const url = `${API_BASE_URL}/reports/map?${params.toString()}`;

    try {
        const response = await fetch(url);
        if (!response.ok) {
            console.error('Failed to load map data:', response.status);
            return;
        }
        const data = await response.json();
        currentReports = data;
        renderMapMarkers(data);
        updateMetrics(data);
    } catch (err) {
        console.error('Error fetching map points:', err);
    }
}

// Render Markers onto the Leaflet Map
function renderMapMarkers(reports) {
    markerClusterGroup.clearLayers();

    if (!reports || reports.length === 0) {
        document.getElementById('active-count').textContent = '0';
        return;
    }

    document.getElementById('active-count').textContent = reports.length;
    const bounds = [];

    reports.forEach(report => {
        const iconEmoji = CATEGORY_ICONS[report.category] || '📌';
        const severityClass = `pin-${(report.severity || 'low').toLowerCase()}`;

        // Custom DivIcon for styling
        const customIcon = L.divIcon({
            className: 'custom-marker-wrapper',
            html: `<div class="custom-pin ${severityClass}" title="${report.title}">${iconEmoji}</div>`,
            iconSize: [32, 32],
            iconAnchor: [16, 16],
            popupAnchor: [0, -18]
        });

        const marker = L.marker([report.latitude, report.longitude], { icon: customIcon });

        // Popup content
        const thumbHtml = report.thumbnail_url 
            ? `<img src="http://localhost:8000/${report.thumbnail_url}" style="width: 100%; height: 100px; object-fit: cover; border-radius: 4px; margin-top: 6px;" alt="Evidence">` 
            : '';

        const popupContent = `
            <div style="font-family: sans-serif; font-size: 12px; min-width: 180px;">
                <div style="font-weight: bold; font-size: 13px; margin-bottom: 4px;">${iconEmoji} ${report.title}</div>
                <div style="margin-bottom: 4px;">
                    <span class="badge badge-${(report.severity || 'low').toLowerCase()}">${report.severity}</span>
                    <span class="badge badge-status">${report.status}</span>
                </div>
                <div style="color: #666; font-size: 11px;">📍 ${report.address || `${report.latitude.toFixed(4)}, ${report.longitude.toFixed(4)}`}</div>
                ${thumbHtml}
            </div>
        `;
        marker.bindPopup(popupContent);

        // Click marker to inspect details in the drawer
        marker.on('click', () => {
            openReportDrawer(report);
        });

        markerClusterGroup.addLayer(marker);
        bounds.push([report.latitude, report.longitude]);
    });

    // Auto-fit map to markers if points exist
    if (bounds.length > 0) {
        map.fitBounds(bounds, { padding: [40, 40], maxZoom: 15 });
    }
}

// Open Inspector Drawer
function openReportDrawer(report) {
    const drawer = document.getElementById('report-drawer');
    const drawerCategory = document.getElementById('drawer-category');
    const drawerBody = document.getElementById('drawer-body');

    const iconEmoji = CATEGORY_ICONS[report.category] || '📌';
    const categoryName = CATEGORY_NAMES[report.category] || report.category;

    drawerCategory.innerHTML = `${iconEmoji} ${categoryName}`;

    const thumbHtml = report.thumbnail_url
        ? `<img src="http://localhost:8000/${report.thumbnail_url}" class="drawer-thumb" alt="Evidence photo">`
        : `<div style="background: rgba(255,255,255,0.03); border: 1px dashed rgba(255,255,255,0.1); border-radius: 6px; padding: 2rem; text-align: center; color: var(--text-muted);">No photographic evidence attached</div>`;

    const reportDate = new Date(report.created_at).toLocaleString();

    drawerBody.innerHTML = `
        ${thumbHtml}
        <div>
            <div class="drawer-field-label">Title</div>
            <div class="drawer-field-val" style="font-weight: 700; font-size: 1rem;">${report.title}</div>
        </div>
        <div style="display: flex; gap: 0.5rem;">
            <div>
                <div class="drawer-field-label">Severity</div>
                <span class="badge badge-${(report.severity || 'low').toLowerCase()}">${report.severity}</span>
            </div>
            <div>
                <div class="drawer-field-label">Status</div>
                <span class="badge badge-status">${report.status}</span>
            </div>
        </div>
        ${report.description ? `
        <div>
            <div class="drawer-field-label">Description</div>
            <div class="drawer-field-val" style="color: var(--text-secondary); line-height: 1.4;">${report.description}</div>
        </div>` : ''}
        <div>
            <div class="drawer-field-label">Approximate Location</div>
            <div class="drawer-field-val">📍 ${report.address || 'Address unlisted'}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted); font-family: monospace;">(${report.latitude.toFixed(5)}, ${report.longitude.toFixed(5)})</div>
        </div>
        <div>
            <div class="drawer-field-label">Reported On</div>
            <div class="drawer-field-val" style="font-size: 0.8rem; color: var(--text-secondary);">${reportDate}</div>
        </div>
    `;

    drawer.classList.add('open');
}

// Close Inspector Drawer
document.getElementById('drawer-close-btn').addEventListener('click', () => {
    document.getElementById('report-drawer').classList.remove('open');
});

// Update Metrics Statistics
function updateMetrics(reports) {
    let criticalCount = 0;
    let inProgressCount = 0;
    let fixedCount = 0;

    reports.forEach(r => {
        if (r.severity === 'CRITICAL' || r.severity === 'HIGH') criticalCount++;
        if (r.status === 'IN_PROGRESS' || r.status === 'ASSIGNED' || r.status === 'VERIFIED') inProgressCount++;
        if (r.status === 'FIXED' || r.status === 'CLOSED') fixedCount++;
    });

    document.getElementById('metric-critical').textContent = criticalCount;
    document.getElementById('metric-in-progress').textContent = inProgressCount;
    document.getElementById('metric-fixed').textContent = fixedCount;
}

// Filter Event Listeners
document.getElementById('btn-apply-filters').addEventListener('click', fetchMapReports);
document.getElementById('filter-category').addEventListener('change', fetchMapReports);
document.getElementById('filter-severity').addEventListener('change', fetchMapReports);
document.getElementById('filter-status').addEventListener('change', fetchMapReports);

document.getElementById('btn-reset-filters').addEventListener('click', () => {
    document.getElementById('filter-category').value = '';
    document.getElementById('filter-severity').value = '';
    document.getElementById('filter-status').value = '';
    fetchMapReports();
});

// --- DIAGNOSTIC MODAL & API HEALTH (Preserved) ---
const diagnosticModal = document.getElementById('diagnostic-modal');
const btnToggleDiagnostics = document.getElementById('btn-toggle-diagnostics');
const modalCloseBtn = document.getElementById('modal-close-btn');

btnToggleDiagnostics.addEventListener('click', () => {
    diagnosticModal.classList.add('active');
    runHealthCheck();
});

modalCloseBtn.addEventListener('click', () => {
    diagnosticModal.classList.remove('active');
});

const healthDot = document.getElementById('health-dot');
const healthStatus = document.getElementById('health-status');
const btnCheck = document.getElementById('btn-check');
const logs = document.getElementById('logs');

function addLog(message, type = 'info') {
    const logLine = document.createElement('div');
    logLine.className = `log-line ${type}`;
    const time = new Date().toLocaleTimeString();
    logLine.textContent = `[${time}] ${message}`;
    logs.appendChild(logLine);
    logs.scrollTop = logs.scrollHeight;
}

async function runHealthCheck() {
    addLog('Initiating backend health diagnostic...', 'info');
    healthDot.className = 'status-dot unknown';
    healthStatus.textContent = 'Contacting server...';

    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();

        if (response.ok && data.status === 'healthy') {
            healthDot.className = 'status-dot healthy';
            healthStatus.textContent = 'API Status: Healthy';
            addLog(`Diagnostic Success: Received status "${data.status}"`, 'success');
        } else {
            healthDot.className = 'status-dot unhealthy';
            healthStatus.textContent = 'API Status: Unhealthy';
            addLog(`Diagnostic Failed: Status ${response.status} - ${JSON.stringify(data)}`, 'error');
        }
    } catch (error) {
        healthDot.className = 'status-dot unhealthy';
        healthStatus.textContent = 'API Status: Unreachable';
        addLog(`Connection Refused: Could not reach backend at ${API_BASE_URL}/health`, 'error');
    }
}

btnCheck.addEventListener('click', runHealthCheck);

// Initialize map on DOM load
window.addEventListener('DOMContentLoaded', initMap);
