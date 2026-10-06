import { useEffect, useState, FormEvent } from 'react';
import { apiErrorMessage, downloadAuditPdf, fetchSystems, formatTime, generateAudit } from '../api/argusApi';

interface AuditRecord {
  id: string;
  generated_at: string;
  content_hash: string | null;
}

function AuditPage() {
  const [systems, setSystems] = useState<{ system_id: string; name: string }[]>([]);
  const [systemId, setSystemId] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [result, setResult] = useState<AuditRecord | null>(null);

  useEffect(() => {
    fetchSystems().then(setSystems)
      .catch(e => setError(apiErrorMessage(e, 'Could not load registered systems.')))
      .finally(() => setLoading(false));
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!systemId || busy) return;
    setBusy(true);
    setError('');
    setResult(null);
    setStatus('Generating audit dossier...');
    try {
      setResult(await generateAudit(systemId));
      setStatus('Audit dossier generated.');
    } catch (e) {
      setError(apiErrorMessage(e, 'Failed to generate audit dossier.'));
      setStatus('');
    } finally {
      setBusy(false);
    }
  }

  async function handleDownload() {
    if (!result) return;
    setDownloading(true);
    setError('');
    try {
      await downloadAuditPdf(result.id);
      setStatus('Audit download started.');
    } catch (e) {
      setError(apiErrorMessage(e, 'Failed to download the audit PDF.'));
    } finally {
      setDownloading(false);
    }
  }

  return <div>
    <h1 className="page-title">Audit Dossier Generator</h1>
    <div className="card">
      {error && <p role="alert" className="error-message">{error}</p>}
      <form onSubmit={handleSubmit}>
        <div className="form-field">
          <label htmlFor="systemId">Registered system</label>
          <select id="systemId" required value={systemId} disabled={loading || busy || downloading}
            onChange={e => { setSystemId(e.target.value); setResult(null); setStatus(''); }}>
            <option value="">{loading ? 'Loading systems...' : 'Select a system'}</option>
            {systems.map(s => <option key={s.system_id} value={s.system_id}>{s.name} ({s.system_id.split('-').pop()})</option>)}
          </select>
        </div>
        {!loading && !systems.length && !error && <p>No registered systems available.</p>}
        <button className="link-button" type="submit" disabled={!systemId || busy || downloading}>
          {busy ? 'Generating...' : 'Generate PDF'}
        </button>
      </form>
      <p role="status">{status}</p>
      {result && <div className="audit-result">
        <p><strong>Record ID:</strong> {result.id}</p>
        <p><strong>Generated:</strong> {formatTime(result.generated_at)}</p>
        <p><strong>SHA-256:</strong> <code>{result.content_hash ?? 'Not supplied'}</code></p>
        <button className="link-button" disabled={downloading} onClick={() => void handleDownload()}>
          {downloading ? 'Downloading...' : 'Download PDF'}
        </button>
      </div>}
    </div>
  </div>;
}

export default AuditPage;
