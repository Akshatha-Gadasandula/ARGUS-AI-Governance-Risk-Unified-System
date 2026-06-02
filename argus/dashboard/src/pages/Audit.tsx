import { useState, FormEvent } from 'react';
import { generateAudit } from '../api/argusApi';

function AuditPage() {
  const [systemId, setSystemId] = useState('');
  const [status, setStatus] = useState('');
  const [result, setResult] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!systemId) return;
    setStatus('Generating audit dossier...');

    try {
      const response = await generateAudit(systemId);
      setResult(`PDF generated at ${response.pdf_path}`);
      setStatus('Completed');
    } catch (error) {
      console.error(error);
      setStatus('Failed to generate audit dossier.');
    }
  };

  return (
    <div>
      <h1 className="page-title">Audit Dossier Generator</h1>
      <div className="card">
        <form onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="systemId">System ID</label>
            <input
              id="systemId"
              type="text"
              value={systemId}
              onChange={(e) => setSystemId(e.target.value)}
              placeholder="Enter registered system ID"
            />
          </div>
          <button className="link-button" type="submit">
            Generate PDF
          </button>
        </form>
        <p className="small-text">{status}</p>
        {result && <p>{result}</p>}
      </div>
    </div>
  );
}

export default AuditPage;
