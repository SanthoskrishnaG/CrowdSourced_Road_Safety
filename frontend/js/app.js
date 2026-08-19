const API_URL = 'http://localhost:8000/api/v1';

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

async function checkHealth() {
    addLog('Initiating backend health diagnostic...', 'info');
    healthDot.className = 'status-dot unknown';
    healthStatus.textContent = 'Contacting server...';
    
    try {
        const response = await fetch(`${API_URL}/health`);
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
        addLog(`Connection Refused: Could not reach backend at ${API_URL}/health`, 'error');
        addLog(`Error details: ${error.message}`, 'error');
    }
}

btnCheck.addEventListener('click', checkHealth);

// Initial check
checkHealth();
