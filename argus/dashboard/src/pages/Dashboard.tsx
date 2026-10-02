import { useEffect, useState } from 'react';
import { fetchSystems, fetchAlerts } from '../api/argusApi';

interface SystemSummary {
  system_id: string;
  name: string;
  risk_tier: string;
  owner_team: string;
  jurisdictions: string[];
}

interface AlertSummary {
  alert_id: string;
  title: string;
  severity: string;
}

function DashboardPage() {
  const [systems, setSystems] = useState<SystemSummary[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);

  useEffect(() => {
    fetchSystems().then(setSystems).catch(console.error);
    fetchAlerts().then(setAlerts).catch(console.error);
  }, []);

  const highRiskCount = systems.filter((s) => s.risk_tier === 'HIGH_RISK').length;
  const totalSystems = systems.length;
  const activeAlerts = alerts.length;

  return (
    <div>
      <h1 className="page-title">ARGUS Dashboard</h1>
      <div className="grid-two">
        <div className="card">
          <h2 className="section-heading">Active AI Systems</h2>
          <p className="metric-value" style={{ fontSize: '2rem', fontWeight: 700 }}>{totalSystems}</p>
          <p>Systems currently registered in ARGUS.</p>
        </div>
        <div className="card">
          <h2 className="section-heading">High-Risk Systems</h2>
          <p className="metric-value" style={{ fontSize: '2rem', fontWeight: 700 }}>{highRiskCount}</p>
          <p>Systems with regulatory risk classification of HIGH_RISK.</p>
        </div>
      </div>
      <div className="grid-two">
        <div className="card">
          <h2 className="section-heading">Open Alerts</h2>
          <p className="metric-value" style={{ fontSize: '2rem', fontWeight: 700 }}>{activeAlerts}</p>
          <p>Alerts generated from monitoring and compliance checks.</p>
        </div>
        <div className="card">
          <h2 className="section-heading">Recent Systems</h2>
          <table className="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Risk</th>
                <th>Owner</th>
              </tr>
            </thead>
            <tbody>
              {systems.slice(0, 5).map((system) => (
                <tr key={system.system_id}>
                  <td>{system.name}</td>
                  <td>{system.risk_tier}</td>
                  <td>{system.owner_team}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default DashboardPage;
