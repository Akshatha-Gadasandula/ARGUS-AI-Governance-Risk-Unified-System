import axios from 'axios';

const configuredBaseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const baseUrl = configuredBaseUrl.endsWith('/api/v1')
  ? configuredBaseUrl
  : `${configuredBaseUrl.replace(/\/$/, '')}/api/v1`;

const client = axios.create({
  baseURL: baseUrl,
  headers: {
    'Content-Type': 'application/json',
  },
});

export async function fetchSystems() {
  const response = await client.get('/registry/systems');
  return response.data;
}

export async function fetchSystem(systemId: string) {
  const response = await client.get(`/registry/systems/${systemId}`);
  return response.data;
}

export async function fetchAlerts(systemId?: string, resolved = false) {
  const response = await client.get('/monitoring/alerts', {
    params: { ...(systemId ? { system_id: systemId } : {}), resolved },
  });
  return response.data;
}

export async function resolveAlert(alertId: string) {
  const response = await client.post(`/monitoring/alerts/${alertId}/resolve`, {
    resolved_by: 'dashboard@argus.local',
  });
  return response.data;
}

export async function fetchLatestSnapshot(systemId: string) {
  const response = await client.get(`/monitoring/systems/${systemId}/snapshots`, { params: { limit: 1 } });
  return response.data[0] ?? null;
}

export function apiErrorMessage(error: unknown, fallback: string) {
  if (axios.isAxiosError(error) && typeof error.response?.data?.detail === 'string') {
    return `${fallback} ${error.response.data.detail}`;
  }
  return fallback;
}

export function formatTime(value?: string) {
  if (!value) return 'Not available';
  const date = new Date(/(?:Z|[+-]\d{2}:\d{2})$/i.test(value) ? value : `${value}Z`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export async function fetchAuditRecords(systemId?: string) {
  const response = await client.get('/audit/records', {
    params: systemId ? { system_id: systemId } : {},
  });
  return response.data;
}

export async function generateAudit(systemId: string) {
  const response = await client.post('/audit/generate-dossier', { system_id: systemId, requested_by: 'dashboard@argus.local' });
  return response.data;
}

export async function downloadAuditPdf(recordId: string) {
  const response = await client.get(`/audit/records/${recordId}/download`, {
    responseType: 'blob',
  });

  const blobUrl = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
  const link = document.createElement('a');
  link.href = blobUrl;
  link.download = `${recordId}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(blobUrl);
}

export default client;
