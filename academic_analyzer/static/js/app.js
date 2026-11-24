/**
 * app.js — Shared JavaScript utilities for Academic Performance Analyzer
 */

// ─── API Utility Object ────────────────────────────────────────────────────────
const API = {
    token: localStorage.getItem('token'),

    getHeaders(isJson = true) {
        const headers = {};
        if (this.token) headers['Authorization'] = 'Bearer ' + this.token;
        if (isJson) headers['Content-Type'] = 'application/json';
        return headers;
    },

    getFormHeaders() {
        const headers = {};
        if (this.token) headers['Authorization'] = 'Bearer ' + this.token;
        return headers;
    },

    setToken(token) {
        this.token = token;
        if (token) localStorage.setItem('token', token);
        else localStorage.removeItem('token');
    },

    clearAuth() {
        this.token = null;
        localStorage.removeItem('token');
        localStorage.removeItem('user');
    }
};

// ─── Generic Fetch Wrapper ─────────────────────────────────────────────────────
async function apiFetch(url, options = {}) {
    const defaults = {
        headers: options.isForm ? API.getFormHeaders() : API.getHeaders(options.isJson !== false)
    };
    const config = Object.assign({}, defaults, options);
    if (options.headers) config.headers = Object.assign({}, defaults.headers, options.headers);

    try {
        const response = await fetch(url, config);

        if (response.status === 401) {
            API.clearAuth();
            window.location.href = '/login';
            return null;
        }

        if (!response.ok) {
            let errorMsg = `HTTP ${response.status}`;
            try {
                const errData = await response.json();
                errorMsg = errData.detail || errData.message || errorMsg;
            } catch {}
            throw new Error(errorMsg);
        }

        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
            return await response.json();
        }
        return await response.text();
    } catch (err) {
        if (err.name === 'TypeError' && err.message.includes('fetch')) {
            throw new Error('Network error — please check your connection.');
        }
        throw err;
    }
}

// ─── Loading Spinner ───────────────────────────────────────────────────────────
let loadingCount = 0;

function showLoading() {
    loadingCount++;
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) overlay.classList.remove('d-none');
}

function hideLoading() {
    loadingCount = Math.max(0, loadingCount - 1);
    if (loadingCount === 0) {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) overlay.classList.add('d-none');
    }
}

// ─── Toast / Flash Messages ────────────────────────────────────────────────────
function showMessage(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    if (!container) return;

    const icons = {
        success: 'fa-check-circle',
        danger: 'fa-times-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };
    const bgColors = {
        success: '#198754',
        danger: '#dc3545',
        warning: '#ffc107',
        info: '#0dcaf0'
    };

    const id = 'toast_' + Date.now();
    const toast = document.createElement('div');
    toast.id = id;
    toast.className = 'toast align-items-center border-0 show';
    toast.style.cssText = `background:${bgColors[type] || bgColors.info};color:${type === 'warning' ? '#000' : '#fff'};`;
    toast.setAttribute('role', 'alert');
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                <i class="fas ${icons[type] || icons.info} me-2"></i>${message}
            </div>
            <button type="button" class="btn-close btn-close-${type === 'warning' ? 'dark' : 'white'} me-2 m-auto"
                    onclick="document.getElementById('${id}').remove()"></button>
        </div>`;
    container.appendChild(toast);
    setTimeout(() => { if (document.getElementById(id)) document.getElementById(id).remove(); }, 4000);
}

// ─── Plotly Chart Renderer ─────────────────────────────────────────────────────
function renderChart(elementId, plotlyData) {
    const el = document.getElementById(elementId);
    if (!el) return;

    try {
        let data;
        if (typeof plotlyData === 'string') {
            data = JSON.parse(plotlyData);
        } else {
            data = plotlyData;
        }

        const layout = Object.assign({
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            font: { family: 'Inter, Segoe UI, sans-serif', size: 12 },
            margin: { t: 40, r: 20, b: 50, l: 50 }
        }, data.layout || {});

        Plotly.newPlot(elementId, data.data || data, layout, {
            responsive: true,
            displayModeBar: true,
            modeBarButtonsToRemove: ['lasso2d', 'select2d'],
            displaylogo: false
        });
    } catch (err) {
        el.innerHTML = `<div class="alert alert-warning m-3"><i class="fas fa-chart-bar me-2"></i>Chart unavailable: ${err.message}</div>`;
    }
}

// ─── Number Formatter ──────────────────────────────────────────────────────────
function fmt(num, decimals = 2) {
    if (num === null || num === undefined || num === '' || isNaN(num)) return 'N/A';
    return Number(num).toFixed(decimals);
}

function fmtPct(num) {
    if (num === null || num === undefined || isNaN(num)) return 'N/A';
    return Number(num).toFixed(1) + '%';
}

// ─── Confirm Delete ────────────────────────────────────────────────────────────
function confirmDelete(url, onSuccess, message = 'Are you sure you want to delete this record? This action cannot be undone.') {
    if (!confirm(message)) return;
    showLoading();
    apiFetch(url, { method: 'DELETE' })
        .then(data => {
            hideLoading();
            showMessage('Record deleted successfully.', 'success');
            if (typeof onSuccess === 'function') onSuccess(data);
        })
        .catch(err => {
            hideLoading();
            showMessage('Delete failed: ' + err.message, 'danger');
        });
}

// ─── Auth Guard ────────────────────────────────────────────────────────────────
function checkAuth() {
    const token = localStorage.getItem('token');
    if (!token) {
        window.location.href = '/login';
        return false;
    }
    API.token = token;
    return true;
}

// ─── Performance Category Badge ────────────────────────────────────────────────
function categoryBadge(category) {
    const map = {
        'Excellent': 'badge-excellent',
        'Good': 'badge-good',
        'Average': 'badge-average',
        'Below Average': 'badge-below-average',
        'At-Risk': 'badge-at-risk'
    };
    const cls = map[category] || 'bg-secondary';
    return `<span class="badge ${cls}">${category || 'N/A'}</span>`;
}

// ─── Z-score category helper ───────────────────────────────────────────────────
function zscore_category(z) {
    if (z === null || z === undefined || isNaN(z)) return 'N/A';
    z = Number(z);
    if (z >= 1.0) return 'Excellent';
    if (z >= 0.0) return 'Good';
    if (z >= -1.0) return 'Average';
    if (z >= -2.0) return 'Below Average';
    return 'At-Risk';
}

// ─── Populate Subject Dropdown ─────────────────────────────────────────────────
async function populateSubjectDropdown(selectId, addAll = true) {
    try {
        const data = await apiFetch('/api/subjects?limit=200');
        const subjects = data.items || data || [];
        const sel = document.getElementById(selectId);
        if (!sel) return;
        sel.innerHTML = '';
        if (addAll) sel.innerHTML = '<option value="">All Subjects</option>';
        subjects.forEach(s => {
            sel.innerHTML += `<option value="${s.id}">${s.subject_code} — ${s.subject_name}</option>`;
        });
    } catch (err) {
        console.error('Could not load subjects:', err);
    }
}

// ─── Build Pagination HTML ─────────────────────────────────────────────────────
function buildPagination(containerId, currentPage, totalPages, onPageChange) {
    const container = document.getElementById(containerId);
    if (!container || totalPages <= 1) {
        if (container) container.innerHTML = '';
        return;
    }
    let html = '<ul class="pagination pagination-sm mb-0">';
    html += `<li class="page-item ${currentPage === 1 ? 'disabled' : ''}">
        <a class="page-link" href="#" onclick="(${onPageChange})(${currentPage - 1});return false;">«</a></li>`;
    const start = Math.max(1, currentPage - 2);
    const end = Math.min(totalPages, currentPage + 2);
    for (let p = start; p <= end; p++) {
        html += `<li class="page-item ${p === currentPage ? 'active' : ''}">
            <a class="page-link" href="#" onclick="(${onPageChange})(${p});return false;">${p}</a></li>`;
    }
    html += `<li class="page-item ${currentPage === totalPages ? 'disabled' : ''}">
        <a class="page-link" href="#" onclick="(${onPageChange})(${currentPage + 1});return false;">»</a></li>`;
    html += '</ul>';
    container.innerHTML = html;
}

// ─── Escape HTML ───────────────────────────────────────────────────────────────
function escHtml(str) {
    if (!str) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}
