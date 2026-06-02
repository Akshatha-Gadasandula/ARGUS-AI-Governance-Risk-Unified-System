import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { fetchSystem } from '../api/argusApi';

function SystemDetailPage() {
  const { systemId } = useParams();
  const [system, setSystem] = useState<any>(null);

  useEffect(() => {
    if (!systemId) return;
    fetchSystem(systemId)
      .then(setSystem)
      .catch(console.error);
  }, [systemId]);

  if (!system) {
    return <div>Loading system details...</div>;
  }

  return (
    <div>
      <h1 className="page-title">System Details</h1>
      <div className="card">
        <div className="section-heading">{system.name}</div>
        <p>{system.purpose}</p>
        <div className="grid-two">
          <div className="card">
            <h3>Risk Profile</h3>
            <p>{system.overall_risk_tier}</p>
          </div>
          <div className="card">
            <h3>Owner</h3>
            <p>{system.owner_team}</p>
          </div>
        </div>
        <div className="card">
          <h3>Regulatory Citations</h3>
          <pre style={{ whiteSpace: 'pre-wrap' }}>
            {JSON.stringify(system.regulatory_citations, null, 2)}
          </pre>
        </div>
      </div>
    </div>
  );
}

export default SystemDetailPage;
