import { Route, Routes } from 'react-router-dom';
import DashboardPage from './pages/Dashboard';
import RegistryPage from './pages/Registry';
import MonitoringPage from './pages/Monitoring';
import AuditPage from './pages/Audit';
import SystemDetailPage from './pages/SystemDetail';
import NotFoundPage from './pages/NotFound';
import './App.css';

function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">ARGUS Governance</div>
        <nav>
          <a href="/">Dashboard</a>
          <a href="/registry">Registry</a>
          <a href="/monitoring">Monitoring</a>
          <a href="/audit">Audit</a>
        </nav>
      </aside>
      <main className="content">
        <Routes>
          <Route path="/" element={<DashboardPage />} />
          <Route path="/registry" element={<RegistryPage />} />
          <Route path="/monitoring" element={<MonitoringPage />} />
          <Route path="/audit" element={<AuditPage />} />
          <Route path="/systems/:systemId" element={<SystemDetailPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
    </div>
  );
}

export default App;
