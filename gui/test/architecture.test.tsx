import { renderToStaticMarkup } from 'react-dom/server';
import { MemoryRouter } from 'react-router-dom';
import fs from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { App } from '../src/App';
import { DIAGRAM_AS_TEXT } from '../src/pages/ArchitecturePage';

const root = path.resolve(__dirname, '..');
const slideHtml = fs.readFileSync(path.join(root, 'public/architecture.html'), 'utf8');
/** Visible text: scripts, styles and tags removed. */
const visible = (html: string) => html.replace(/<(script|style)[\s\S]*?<\/\1>/g, ' ').replace(/<[^>]+>/g, ' ').replace(/&[a-z#0-9x]+;/gi, ' ');
const at = (route: string) => renderToStaticMarkup(<MemoryRouter initialEntries={[route]}><App /></MemoryRouter>);
const BANNED = /\bsecure\b|\bsafe\b|injection-proof|\bNAT\b|\bPHI\b/i;
const HOME_BANNED = /optimi[sz]|\bRCM\b|revenue|orchestrat|full NVIDIA stack/i;

describe('Architecture page', () => {
  const html = at('/architecture');
  it('renders the route with eyebrow, h1 and subtitle', () => {
    expect(html).toContain('Architecture</p>');
    expect(html).toContain('<h2 class="page-title">How it works</h2>');
    expect(html).toContain('Nemotron reasons, OpenShell contains it, and NemoClaw deploys it.');
  });
  it('shows the slide in an iframe with a title and src /architecture.html, no inner scrolling', () => {
    expect(html).toMatch(/<iframe src="\/architecture\.html" title="Architecture of the demo: Nemotron, OpenShell, NemoClaw and the open-source agent"/);
    expect(html).toContain('scrolling="no"');
  });
  it('has the Full screen button and the PNG download link', () => {
    expect(html).toContain('>Full screen<');
    expect(html).toMatch(/<a class="btn" href="\/architecture\.png" download="architecture\.png">Download PNG<\/a>/);
    expect(fs.existsSync(path.join(root, 'public/architecture.png'))).toBe(true);
  });
  it('has the text alternative, with no numbers', () => {
    expect(html).toContain('Read the diagram as text');
    for (const line of DIAGRAM_AS_TEXT) {
      expect(html).toContain(line.replace(/'/g, '&#x27;'));
      expect(line.replace('Nemotron 3.5 Super', '')).not.toMatch(/\d/); // no figures; the model name is the only digits
    }
    expect(DIAGRAM_AS_TEXT).toHaveLength(7);
  });
  it('the nav order is Home, Architecture, Case, Containment, Scorecard', () => {
    const nav = html.slice(html.indexOf('aria-label="Main"'), html.indexOf('</nav>'));
    expect([...nav.matchAll(/class="nav__link"[^>]*>([^<]+)</g)].map((m) => m[1])).toEqual(['Home', 'Architecture', 'Case', 'Containment', 'Scorecard']);
    expect(nav).toMatch(/<a[^>]*href="\/architecture"[^>]*aria-current="page"|<a[^>]*aria-current="page"[^>]*href="\/architecture"/);
  });
});

describe('wording', () => {
  it('the slide (visible text), the Architecture page and Home have no banned word', () => {
    for (const [name, text] of [['architecture.html', visible(slideHtml)], ['architecture page', visible(at('/architecture'))], ['home', visible(at('/'))]] as const) {
      expect(text, name).not.toMatch(BANNED);
    }
  });
  it('the slide and Home do not say optimization, RCM, revenue, orchestrat or "full NVIDIA stack"', () => {
    for (const [name, text] of [['architecture.html', visible(slideHtml)], ['home', visible(at('/'))]] as const) {
      expect(text, name).not.toMatch(HOME_BANNED);
    }
  });
  it('the slide is the provided file, untouched by React: it has its own scale-to-fit script', () => {
    expect(slideHtml).toMatch(/<script/);
    expect(slideHtml).toContain('How the demo works');
  });
});

describe('layout rules (checked in a browser, see docs/STATUS.md)', () => {
  it('the frame is sized by CSS to the available width and to the viewport height minus the header', () => {
    const css = fs.readFileSync(path.join(root, 'src/styles/global.css'), 'utf8');
    expect(css).toMatch(/\.arch__frame\s*{[^}]*aspect-ratio: 16 \/ 9[^}]*max-height: calc\(100vh - 72px\)[^}]*border: 1px solid var\(--line\)[^}]*border-radius: 16px/);
  });
});
