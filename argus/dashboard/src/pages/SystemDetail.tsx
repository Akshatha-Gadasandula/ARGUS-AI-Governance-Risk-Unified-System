import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { downloadAuditPdf, fetchAuditRecords, fetchSystem } from '../api/argusApi';

function SystemDetailPage() {
  const { systemId } = useParams();
  const [system, setSystem] = useState<any>(null);
  const [latestAuditRecordId, setLatestAuditRecordId] = useState<string | null>(null);
  const [auditStatus, setAuditStatus] = useState('');

  useEffect(() => {
    if (!systemId) return;
    fetchSystem(systemId)
      .then(setSystem)
      .catch(console.error);

    fetchAuditRecords(systemId)
      .then((records) => setLatestAuditRecordId(records?.[0]?.id ?? null))
      .catch(console.error);
  }, [systemId]);

  const handleDownloadAudit = async () => {
    if (!latestAuditRecordId) {
      setAuditStatus('No audit report found for this system.');
      return;
    }

    setAuditStatus('Downloading audit report...');
    try {
      await downloadAuditPdf(latestAuditRecordId);
      setAuditStatus('Audit report downloaded.');
    } catch (error) {
      console.error(error);
      setAuditStatus('Failed to download audit report.');
    }
  };

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
        <div className="card">
          <h3>Audit Report</h3>
          <button className="link-button" type="button" onClick={handleDownloadAudit}>
            Download Latest Audit Report
          </button>
          {auditStatus && <p className="small-text">{auditStatus}</p>}
          {!latestAuditRecordId && <p className="small-text">No audit report has been generated for this system yet.</p>}
        </div>
      </div>
    </div>
  );
}

export default SystemDetailPage;
