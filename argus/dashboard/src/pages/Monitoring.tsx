import { useEffect, useState } from 'react';
import { apiErrorMessage, fetchAlerts, fetchSystem, fetchSystems, formatTime, resolveAlert } from '../api/argusApi';

export interface Alert {
  id: string;
  system_id: string;
  alert_type: string;
  severity: string;
  title: string;
  payload?: { metric?: string; affected_feature?: string | null; value?: number; threshold?: number; protected_attribute?: string; compared_groups?: string[] };
  regulatory_references?: string[];
  created_at: string;
  resolved: boolean;
}

export function metricLabel(metric?: string) {
  if (!metric) return 'Not supplied';
  return metric.toLowerCase() === 'psi' ? 'PSI' : metric.replace(/_/g, ' ');
}

export function metricValue(value?: number | null) {
  return typeof value === 'number' ? value.toFixed(4) : 'Not supplied';
}

function referenceText(reference: string) {
  return reference.split(';').map(part => {
    const text = part.trim();
    return /rbi/i.test(text) && /unverified|corpus|not assessed/i.test(text)
      ? 'RBI: not assessed (no corpus indexed)' : text;
  }).join('; ');
}

export function AlertDetails({ alert }: { alert: Alert }) {
  const metric = metricLabel(alert.payload?.metric);
  return <>
    <p><strong>{alert.title.replace(/psi violation/gi, 'PSI violation')}</strong></p>
    <p>Type: {alert.alert_type.replace(/_/g, ' ')} | <span className={`status-pill ${alert.severity}`}>{alert.severity}</span></p>
    <p>{metric}{alert.payload?.affected_feature ? `: ${alert.payload.affected_feature}` : ' | Feature not supplied'}</p>
    {alert.alert_type === 'FAIRNESS_VIOLATION' && <p>
      {alert.payload?.protected_attribute && alert.payload.compared_groups?.length
        ? `${alert.payload.protected_attribute}: ${alert.payload.compared_groups.join(' vs ')}`
        : 'Protected attribute and compared groups not supplied'}
    </p>}
    <p>Value {metricValue(alert.payload?.value)} / threshold {metricValue(alert.payload?.threshold)}</p>
    <p>Regulatory references: {(alert.regulatory_references ?? []).map(referenceText).join('; ') || 'Not supplied'}</p>
    <p>Created: {formatTime(alert.created_at)} | {alert.resolved ? 'Resolved' : 'Open'}</p>
  </>;
}

function MonitoringPage() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [systemNames, setSystemNames] = useState<Record<string, string>>({});
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [resolving, setResolving] = useState<string | null>(null);

  async function refreshAlerts() {
    const [open, resolved] = await Promise.all([fetchAlerts(), fetchAlerts(undefined, true)]);
    setAlerts([...open, ...resolved].sort((a, b) => b.created_at.localeCompare(a.created_at)));
  }

  useEffect(() => {
    async function load() {
      try {
        const systems = await fetchSystems();
        // Alerts contain database UUIDs; registry summaries contain public system IDs.
        const details = await Promise.all(systems.map((s: { system_id: string }) => fetchSystem(s.system_id)));
        setSystemNames(Object.fromEntries(details.flatMap(s => [[s.id, s.name], [s.system_id, s.name]])));
        await refreshAlerts();
      } catch (e) {
        setError(apiErrorMessage(e, 'Could not load monitoring data.'));
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, []);

  async function handleResolve(id: string) {
    setResolving(id);
    setError('');
    try {
      await resolveAlert(id);
      await refreshAlerts();
    } catch (e) {
      setError(apiErrorMessage(e, 'Could not resolve the alert or refresh the list.'));
    } finally {
      setResolving(null);
    }
  }

  return <div>
    <h1 className="page-title">Monitoring</h1>
    {error && <p role="alert" className="error-message">{error}</p>}
    {loading ? <p>Loading alerts...</p> : <div className="detail-stack">
      {alerts.length === 0 && !error && <p>No alerts found.</p>}
      {alerts.map(alert => <article className="card" key={alert.id}>
        <h2>{systemNames[alert.system_id] ?? `System ${alert.system_id}`}</h2>
        <AlertDetails alert={alert} />
        {!alert.resolved && <button className="link-button" disabled={resolving !== null} onClick={() => void handleResolve(alert.id)}>
          {resolving === alert.id ? 'Resolving...' : 'Resolve'}
        </button>}
      </article>)}
    </div>}
  </div>;
}

export default MonitoringPage;
