import axios from 'axios';

const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

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

export async function fetchAlerts() {
  const response = await client.get('/monitoring/alerts');
  return response.data;
}

export async function generateAudit(systemId: string) {
  const response = await client.post('/audit/generate-dossier', { system_id: systemId, requested_by: 'dashboard@argus.local' });
  return response.data;
}

export default client;
