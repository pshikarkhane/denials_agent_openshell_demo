import { Route, Routes } from 'react-router-dom';
import { Header } from './components/Header';
import { Home } from './pages/Home';
import { CasePage } from './pages/CasePage';
import { ContainmentPage } from './pages/SummaryPages';
import { ScorecardPage } from './pages/ScorecardPage';

export function App() {
  return (
    <>
      <a className="skip-link" href="#main">Skip to content</a>
      <Header />
      <main id="main" className="page">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/case/:caseId" element={<CasePage />} />
          <Route path="/containment" element={<ContainmentPage />} />
          <Route path="/scorecard" element={<ScorecardPage />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </main>
    </>
  );
}

function NotFound() {
  return (
    <section>
      <h2 className="page-title">Page not found</h2>
      <p className="muted">Use the navigation above to go back.</p>
    </section>
  );
}
