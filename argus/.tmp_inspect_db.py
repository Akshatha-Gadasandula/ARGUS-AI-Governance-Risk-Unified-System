import os
import sqlite3
from pathlib import Path

for path in [Path('fallback_argus.db'), Path('../fallback_argus.db')]:
    print('checking', path.resolve(), 'exists', path.exists())

conn = sqlite3.connect('fallback_argus.db')
cur = conn.cursor()
print('tables', cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall())
print('ai_systems', cur.execute("SELECT COUNT(*) FROM ai_systems").fetchone())
rows = cur.execute("SELECT system_id, name, purpose, risk_classification_reasoning, monitoring_enabled, registered_at FROM ai_systems ORDER BY registered_at DESC LIMIT 10").fetchall()
for row in rows:
    print('system', row)

print('fairness_snapshots', cur.execute("SELECT COUNT(*) FROM fairness_snapshots").fetchone())
for row in cur.execute("SELECT system_id, demographic_parity_diff, equalized_odds_diff, psi_score, evaluated_at, sample_size FROM fairness_snapshots ORDER BY evaluated_at DESC LIMIT 10").fetchall():
    print('snapshot', row)

print('governance_alerts', cur.execute("SELECT COUNT(*) FROM governance_alerts").fetchone())
for row in cur.execute("SELECT system_id, title, severity, created_at, resolved FROM governance_alerts ORDER BY created_at DESC LIMIT 10").fetchall():
    print('alert', row)
