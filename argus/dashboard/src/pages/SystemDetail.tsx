import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { apiErrorMessage, downloadAuditPdf, fetchAlerts, fetchAuditRecords, fetchLatestSnapshot, fetchSystem, formatTime } from '../api/argusApi';
import { Alert, AlertDetails, metricValue } from './Monitoring';

interface Citation {
  canonical_citation?: string;
  article?: string;
  annex?: string | null;
  point?: string | null;
  title?: string;
  page_number?: number;
  page?: number;
  citation_incomplete?: boolean;
}

interface Framework {
  status?: string;
  risk_tier?: string | null;
  confidence?: number | null;
  llm_provider?: string;
  llm_model?: string | null;
  needs_review?: boolean;
  needs_review_reasons?: string[];
  reasoning?: string;
  citations?: Citation[];
  exclusions_checked?: Citation[];
  retrieved_provisions?: Record<string, any>[];
}

function citationPages(citation: Citation, provisions: Record<string, any>[]) {
  if (citation.page_number != null || citation.page != null) return `Page ${citation.page_number ?? citation.page}`;
  const article = /^(?:Article\s+)?(\d+)(?:\(|$)/i.exec(citation.canonical_citation ?? citation.article ?? '');
  const annex = citation.annex ?? /^Annex\s+([IVXLCDM]+)/i.exec(citation.article ?? '')?.[1];
  const matches = provisions.filter(p => article
    ? p.section_type === 'article' && String(p.article_number) === article[1]
    : annex && p.section_type === 'annex' && p.annex_id === annex && (!citation.point ||
      `${p.annex_point}${p.annex_subpoint ? `(${p.annex_subpoint})` : ''}` === citation.point));
  const pages = [...new Set(matches.map(p => p.page_number ?? (typeof p.page === 'number' ? p.page + 1 : undefined))
    .filter((p): p is number => typeof p === 'number'))].sort((a, b) => a - b);
  return pages.length ? `Retrieved context page${pages.length > 1 ? 's' : ''}: ${pages.join(', ')}` : 'Page not supplied';
}

function CitationList({ citations, provisions }: { citations: Citation[]; provisions: Record<string, any>[] }) {
  return citations.length ? <ul className="citation-list">
    {citations.map((c, index) => <li key={index}>
      <strong>{c.canonical_citation ?? c.article ?? 'Citation not supplied'}</strong>
      <p>{c.title || 'Title not supplied'}</p>
      <p>{citationPages(c, provisions)}{c.citation_incomplete ? ' | Incomplete citation' : ''}</p>
    </li>)}
  </ul> : <p>None returned.</p>;
}

function SystemDetailPage() {
  const { systemId } = useParams();
  const [system, setSystem] = useState<any>(null);
  const [snapshot, setSnapshot] = useState<any>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [latestAuditRecordId, setLatestAuditRecordId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [extraErrors, setExtraErrors] = useState<string[]>([]);
  const [auditStatus, setAuditStatus] = useState('');
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!systemId) return;
    let active = true;
    setLoading(true);
    setSystem(null);
    setSnapshot(null);
    setAlerts([]);
    setLatestAuditRecordId(null);
    setError('');
    setExtraErrors([]);
    setAuditStatus('');
    async function load() {
      const results = await Promise.allSettled([
        fetchSystem(systemId!), fetchAuditRecords(systemId), fetchLatestSnapshot(systemId!),
        Promise.all([fetchAlerts(systemId), fetchAlerts(systemId, true)]),
      ]);
      if (!active) return;
      const errors: string[] = [];
      if (results[0].status === 'fulfilled') setSystem(results[0].value);
      else setError(apiErrorMessage(results[0].reason, 'Could not load system details.'));
      if (results[1].status === 'fulfilled') setLatestAuditRecordId(results[1].value?.[0]?.id ?? null);
      else errors.push('Could not load audit records.');
      if (results[2].status === 'fulfilled') setSnapshot(results[2].value);
      else errors.push('Could not load the latest fairness snapshot.');
      if (results[3].status === 'fulfilled') setAlerts(results[3].value.flat().sort((a, b) => b.created_at.localeCompare(a.created_at)));
      else errors.push('Could not load system alerts.');
      setExtraErrors(errors);
      setLoading(false);
    }
    void load();
    return () => { active = false; };
  }, [systemId]);

  async function handleDownloadAudit() {
    if (!latestAuditRecordId) return;
    setDownloading(true);
    setAuditStatus('Downloading audit report...');
    try {
      await downloadAuditPdf(latestAuditRecordId);
      setAuditStatus('Audit download started.');
    } catch (e) {
      setAuditStatus(apiErrorMessage(e, 'Failed to download audit report.'));
    } finally {
      setDownloading(false);
    }
  }

  if (loading) return <p>Loading system details...</p>;
  if (!system) return <p role="alert" className="error-message">{error || 'System not found.'}</p>;

  return <div>
    <h1 className="page-title">{system.name}</h1>
    {extraErrors.map(message => <p key={message} role="alert" className="error-message">{message}</p>)}
    <div className="detail-stack">
      <section className="card">
        <p>{system.purpose}</p>
        <p><strong>System ID:</strong> {system.system_id}</p>
        <p><strong>Overall risk:</strong> {system.risk_tier ?? 'Not assessed'} | <strong>Owner:</strong> {system.owner_team}</p>
      </section>
      <section>
        <h2>Regulatory assessment</h2>
        <div className="detail-stack">
          {Object.entries((system.regulatory_citations ?? {}) as Record<string, Framework>).map(([name, framework]) => <article className="card" key={name}>
            <h3>{name.replace(/_/g, ' ')}</h3>
            <p><strong>Status:</strong> {(framework.status ?? 'Not supplied').replace(/_/g, ' ')}</p>
            <p><strong>Tier:</strong> {framework.risk_tier ?? 'Not assessed'} | <strong>Confidence:</strong> {typeof framework.confidence === 'number' ? `${(framework.confidence * 100).toFixed(0)}%` : 'Not supplied'}</p>
            <p><strong>Provider:</strong> {framework.llm_provider ?? 'Not supplied'} | <strong>Model:</strong> {framework.llm_model ?? 'None'}</p>
            <p><strong>Needs review:</strong> {framework.needs_review === undefined ? 'Not supplied' : framework.needs_review ? 'Yes' : 'No'}</p>
            <p><strong>Review reasons:</strong></p>
            {(framework.needs_review_reasons ?? []).length ? <ul>{framework.needs_review_reasons!.map(reason => <li key={reason}>{reason.replace(/_/g, ' ')}</li>)}</ul> : <p>No reasons returned.</p>}
            <h4>Reasoning</h4>
            <p className="preserve-text">{framework.reasoning || 'Not supplied'}</p>
            <h4>Supporting citations</h4>
            <CitationList citations={framework.citations ?? []} provisions={framework.retrieved_provisions ?? []} />
            {!!framework.exclusions_checked?.length && <>
              <h4>Exclusions checked</h4>
              <CitationList citations={framework.exclusions_checked} provisions={framework.retrieved_provisions ?? []} />
            </>}
          </article>)}
          {!Object.keys(system.regulatory_citations ?? {}).length && <p>No framework assessments returned.</p>}
        </div>
      </section>
      <section className="card">
        <h2>Latest fairness snapshot</h2>
        {snapshot ? <>
          <p>Evaluated: {formatTime(snapshot.evaluated_at)} | Samples: {snapshot.sample_size}</p>
          <p>Demographic parity difference: {metricValue(snapshot.demographic_parity_diff)}</p>
          <p>Equalized odds difference: {metricValue(snapshot.equalized_odds_diff)}</p>
          <p>Overall PSI: {metricValue(snapshot.psi_score)}</p>
          <p>Drifted features: {(snapshot.drifted_features ?? []).join(', ') || 'None'}</p>
        </> : <p>{extraErrors.includes('Could not load the latest fairness snapshot.') ? 'Snapshot unavailable.' : 'No snapshot recorded yet.'}</p>}
      </section>
      <section>
        <h2>System alerts</h2>
        {alerts.length ? <div className="detail-stack">{alerts.map(alert => <article className="card" key={alert.id}><AlertDetails alert={alert} /></article>)}</div>
          : <p>{extraErrors.includes('Could not load system alerts.') ? 'Alerts unavailable.' : 'No alerts recorded.'}</p>}
      </section>
      <section className="card">
        <h2>Model card</h2>
        {system.model_card ? <pre className="preserve-text model-card">{system.model_card}</pre> : <p>No model card returned.</p>}
      </section>
      <section className="card">
        <h2>Audit report</h2>
        <button className="link-button" type="button" disabled={!latestAuditRecordId || downloading} onClick={() => void handleDownloadAudit()}>
          {downloading ? 'Downloading...' : 'Download latest audit report'}
        </button>
        <p role="status">{auditStatus}</p>
        {!latestAuditRecordId && <p>{extraErrors.includes('Could not load audit records.') ? 'Audit records unavailable.' : 'No audit report recorded yet.'}</p>}
      </section>
    </div>
  </div>;
}

export default SystemDetailPage;
