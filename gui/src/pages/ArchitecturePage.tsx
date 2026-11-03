import { useRef } from 'react';

const SLIDE = `${import.meta.env.BASE_URL}architecture.html`;
const PNG = `${import.meta.env.BASE_URL}architecture.png`;

/** Plain-text version of the slide. Static; no numbers. */
export const DIAGRAM_AS_TEXT = [
  'The case folder is copied into the sandbox read-only, and the answer key is not in it.',
  'The agent runs the six skills inside the OpenShell sandbox that NemoClaw deploys.',
  'The only allowed connection is the model endpoint, Nemotron 3.5 Super (preview), and the route is swappable.',
  'OpenShell logs the connections it allows and denies.',
  'The outputs leave the sandbox.',
  'Independent judges score them outside the sandbox, with the answer key.',
  'This GUI replays recorded runs.',
];

export function ArchitecturePage() {
  const frame = useRef<HTMLDivElement>(null);

  const fullScreen = () => {
    const el = frame.current;
    if (el?.requestFullscreen) el.requestFullscreen().catch(() => window.location.assign(SLIDE));
    else window.location.assign(SLIDE);
  };

  return (
    <section className="arch">
      <p className="eyebrow">Architecture</p>
      <h2 className="page-title">How it works</h2>
      <p className="arch__sub">Nemotron reasons, OpenShell contains it, and NemoClaw deploys it.</p>

      <div className="arch__actions">
        <button type="button" className="btn" onClick={fullScreen}>Full screen</button>
        <a className="btn" href={PNG} download="architecture.png">Download PNG</a>
      </div>

      <div className="arch__frame" ref={frame}>
        <iframe src={SLIDE} title="Architecture of the demo: Nemotron, OpenShell, NemoClaw and the open-source agent" scrolling="no" className="arch__iframe" />
      </div>

      <details className="arch__text">
        <summary>Read the diagram as text</summary>
        <ul className="ct-list">
          {DIAGRAM_AS_TEXT.map((t) => <li key={t}>{t}</li>)}
        </ul>
      </details>
    </section>
  );
}
