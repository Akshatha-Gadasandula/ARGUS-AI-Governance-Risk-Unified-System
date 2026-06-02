import { useEffect, useState } from 'react';
import { fetchAlerts } from '../api/argusApi';

function MonitoringPage() {
  const [alerts, setAlerts] = useState<any[]>([]);

  useEffect(() => {
    fetchAlerts().then(setAlerts).catch(console.error);
  }, []);

  return (
    <div>
      <h1 className="page-title">Monitoring</h1>
      <div className="card">
        <div className="section-heading">Open Alerts</div>
        <table className="table">
          <thead>
            <tr>
              <th>Title</th>
              <th>Severity</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {alerts.length === 0 ? (
              <tr>
                <td colSpan={3}>No active alerts found.</td>
              </tr>
            ) : (
              alerts.map((alert) => (
                <tr key={alert.alert_id}>
                  <td>{alert.title}</td>
                  <td>{alert.severity}</td>
                  <td>{alert.resolved ? 'Resolved' : 'Open'}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default MonitoringPage;
