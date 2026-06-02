import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchSystems } from '../api/argusApi';

interface SystemSummary {
  system_id: string;
  name: string;
  overall_risk_tier: string;
  owner_team: string;
  jurisdictions: string[];
}

function RegistryPage() {
  const [systems, setSystems] = useState<SystemSummary[]>([]);

  useEffect(() => {
    fetchSystems().then(setSystems).catch(console.error);
  }, []);

  return (
    <div>
      <h1 className="page-title">AI System Registry</h1>
      <div className="card">
        <div className="section-heading">Registered AI Systems</div>
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Risk Tier</th>
              <th>Owner Team</th>
              <th>Jurisdictions</th>
            </tr>
          </thead>
          <tbody>
            {systems.map((system) => (
              <tr key={system.system_id}>
                <td>
                  <Link to={`/systems/${system.system_id}`}>{system.name}</Link>
                </td>
                <td>{system.overall_risk_tier}</td>
                <td>{system.owner_team}</td>
                <td>{system.jurisdictions.join(', ')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default RegistryPage;
