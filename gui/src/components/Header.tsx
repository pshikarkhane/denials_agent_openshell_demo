import { Link, useLocation } from 'react-router-dom';

const NAV: { to: string; label: string; match: (path: string) => boolean }[] = [
  { to: '/', label: 'Home', match: (p) => p === '/' },
  { to: '/case/C-0005', label: 'Case', match: (p) => p.startsWith('/case/') },
  { to: '/containment', label: 'Containment', match: (p) => p.startsWith('/containment') },
  { to: '/scorecard', label: 'Scorecard', match: (p) => p.startsWith('/scorecard') },
];

export function Header() {
  const { pathname } = useLocation();
  return (
    <header className="site-header">
      <div className="site-header__inner">
        <div className="brand">
          <span className="brand__mark" aria-hidden="true" />
          <span className="brand__name">Denial Appeals Agent</span>
          <span className="brand__sub">R1 x NVIDIA demo</span>
        </div>

        <nav className="nav" aria-label="Main">
          {NAV.map((n) => (
            <Link key={n.label} to={n.to} className="nav__link" aria-current={n.match(pathname) ? 'page' : undefined}>
              {n.label}
            </Link>
          ))}
        </nav>

        <div className="header-tools">
          <div className="segmented" role="group" aria-label="Data mode">
            <button type="button" className="segmented__btn" aria-pressed="true">Cached</button>
            <span title="Not available yet" className="segmented__tip">
              <button type="button" className="segmented__btn" aria-pressed="false" disabled>Live demo</button>
            </span>
          </div>
          <span className="pill pill--green"><span className="dot" aria-hidden="true" />SANDBOXED</span>
        </div>
      </div>
    </header>
  );
}
