async function api(path, options = {}) {
    const resp = await fetch(path, {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options,
    });
    if (resp.status === 401) {
        window.location.href = '/login';
        return;
    }
    if (!resp.ok) {
        const err = await resp.json().catch(() => ({ detail: resp.statusText }));
        throw new Error(err.detail || JSON.stringify(err));
    }
    if (resp.headers.get('content-type')?.includes('application/json')) {
        return resp.json();
    }
    return resp;
}

async function logout() {
    await fetch('/api/auth/logout', { method: 'POST' });
    window.location.href = '/login';
}

function formatDuration(seconds) {
    if (!seconds && seconds !== 0) return '--';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h}h ${m}m`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
}

function formatCurrency(val) {
    if (val === null || val === undefined) return '--';
    return '$' + parseFloat(val).toFixed(2);
}

function formatDate(iso) {
    if (!iso) return '--';
    return new Date(iso).toLocaleString();
}
