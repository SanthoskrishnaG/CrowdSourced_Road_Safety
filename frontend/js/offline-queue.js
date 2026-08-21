/**
 * RoadOps Offline Drafts Queue & IndexedDB Manager
 * Provides offline queueing for citizen hazard reports and automated background sync.
 */

const DB_NAME = 'RoadSafetyOfflineDB';
const DB_VERSION = 1;
const STORE_NAME = 'draft_reports';

let dbInstance = null;

// Initialize IndexedDB
function initOfflineDB() {
    return new Promise((resolve, reject) => {
        if (!window.indexedDB) {
            console.warn('IndexedDB not supported in this environment.');
            resolve(null);
            return;
        }

        const request = window.indexedDB.open(DB_NAME, DB_VERSION);

        request.onerror = (e) => {
            console.error('IndexedDB open error:', e);
            reject(e);
        };

        request.onsuccess = (e) => {
            dbInstance = e.target.result;
            console.log('IndexedDB initialized successfully.');
            updateOfflineBadgeUI();
            resolve(dbInstance);
        };

        request.onupgradeneeded = (e) => {
            const db = e.target.result;
            if (!db.objectStoreNames.contains(STORE_NAME)) {
                const store = db.createObjectStore(STORE_NAME, { keyPath: 'id', autoIncrement: true });
                store.createIndex('created_at', 'created_at', { unique: false });
                console.log('IndexedDB draft_reports store created.');
            }
        };
    });
}

// Save draft report to local IndexedDB
async function saveOfflineDraft(reportData, imageBase64List = []) {
    if (!dbInstance) await initOfflineDB();
    if (!dbInstance) throw new Error('IndexedDB unavailable');

    return new Promise((resolve, reject) => {
        const tx = dbInstance.transaction([STORE_NAME], 'readwrite');
        const store = tx.objectStore(STORE_NAME);

        const draft = {
            ...reportData,
            images: imageBase64List,
            created_at: new Date().toISOString(),
            sync_status: 'PENDING'
        };

        const req = store.add(draft);
        req.onsuccess = () => {
            console.log('Offline draft saved:', draft);
            updateOfflineBadgeUI();
            resolve(req.result);
        };
        req.onerror = (e) => reject(e);
    });
}

// Retrieve all queued drafts
async function getQueuedDrafts() {
    if (!dbInstance) await initOfflineDB();
    if (!dbInstance) return [];

    return new Promise((resolve, reject) => {
        const tx = dbInstance.transaction([STORE_NAME], 'readonly');
        const store = tx.objectStore(STORE_NAME);
        const req = store.getAll();

        req.onsuccess = () => resolve(req.result || []);
        req.onerror = (e) => reject(e);
    });
}

// Delete draft after successful server synchronization
async function deleteOfflineDraft(id) {
    if (!dbInstance) await initOfflineDB();
    if (!dbInstance) return;

    return new Promise((resolve, reject) => {
        const tx = dbInstance.transaction([STORE_NAME], 'readwrite');
        const store = tx.objectStore(STORE_NAME);
        const req = store.delete(id);

        req.onsuccess = () => {
            updateOfflineBadgeUI();
            resolve();
        };
        req.onerror = (e) => reject(e);
    });
}

// Sync all queued drafts to backend API
async function syncOfflineDrafts(apiBaseUrl, authHeaders) {
    const drafts = await getQueuedDrafts();
    if (!drafts || drafts.length === 0) return { synced: 0, failed: 0 };

    console.log(`[Offline Sync] Synchronizing ${drafts.length} queued drafts...`);
    let synced = 0;
    let failed = 0;

    for (const draft of drafts) {
        try {
            const payload = {
                category: draft.category,
                title: draft.title,
                description: draft.description,
                severity: draft.severity,
                latitude: draft.latitude,
                longitude: draft.longitude,
                address: draft.address,
                phone_number: draft.phone_number
            };

            const res = await fetch(`${apiBaseUrl}/reports`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...authHeaders
                },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                const report = await res.json();
                console.log(`[Offline Sync] Draft synced successfully as Report #${report.id}`);
                await deleteOfflineDraft(draft.id);
                synced++;
            } else {
                console.warn(`[Offline Sync] Failed to sync draft #${draft.id}:`, res.status);
                failed++;
            }
        } catch (err) {
            console.error(`[Offline Sync] Network error syncing draft #${draft.id}:`, err);
            failed++;
        }
    }

    updateOfflineBadgeUI();
    return { synced, failed };
}

// Update offline banner and queue counter badge in UI
async function updateOfflineBadgeUI() {
    const banner = document.getElementById('offline-banner');
    const badge = document.getElementById('offline-queue-badge');
    const countEl = document.getElementById('offline-queue-count');

    const drafts = await getQueuedDrafts();
    const count = drafts.length;

    const isOffline = !navigator.onLine;

    if (banner) {
        if (isOffline) {
            banner.style.display = 'flex';
            banner.innerHTML = `
                <div class="offline-pill"><span class="pulse-dot"></span> Offline Mode</div>
                <span>You are currently disconnected. Reports will be saved locally and auto-synced upon reconnecting. (${count} queued)</span>
            `;
        } else if (count > 0) {
            banner.style.display = 'flex';
            banner.innerHTML = `
                <div class="online-pill">Back Online</div>
                <span>${count} draft reports stored locally.</span>
                <button id="btn-manual-sync" class="btn-sync-now" onclick="window.triggerManualSync()">Sync Now (${count})</button>
            `;
        } else {
            banner.style.display = 'none';
        }
    }

    if (badge && countEl) {
        if (count > 0) {
            badge.style.display = 'inline-flex';
            countEl.textContent = count;
        } else {
            badge.style.display = 'none';
        }
    }
}

// Connectivity Event Listeners
window.addEventListener('online', () => {
    console.log('[Network] Device transitioned to ONLINE.');
    updateOfflineBadgeUI();
    if (typeof window.triggerManualSync === 'function') {
        window.triggerManualSync();
    }
});

window.addEventListener('offline', () => {
    console.log('[Network] Device transitioned to OFFLINE.');
    updateOfflineBadgeUI();
});

// Auto-init on script load
document.addEventListener('DOMContentLoaded', () => {
    initOfflineDB();
});
