import type { ReactNode } from 'react';
import type { DataRoomBlock, DataRoomDoc, DataRoomRow, DataRoomView } from '../../data/types';
import { Chip } from '../Chip';
import { openedLabel, type Selection } from './selection';

const esc = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/** Wraps each occurrence of a matched value in <mark>. */
export function Highlight({ text, tokens }: { text: string; tokens: string[] }): ReactNode {
  const needles = [...new Set(tokens.map((t) => t.replace(/^\$/, '')))].filter(Boolean).sort((a, b) => b.length - a.length);
  if (!needles.length) return text;
  const re = new RegExp(`(${needles.map(esc).join('|')})`, 'g');
  return text.split(re).map((part, i) => (needles.includes(part) ? <mark key={i} className="dr-mark">{part}</mark> : part));
}

function Lines({ doc, tokens, only }: { doc: DataRoomDoc; tokens: string[]; only?: number[] }) {
  const rows = doc.lines.map((l, i) => ({ l, n: i + 1 })).filter((r) => (only ? only.includes(r.n) : true));
  return (
    <ol className="dr-lines" aria-label={`Lines of ${doc.path}`}>
      {rows.map(({ l, n }) => (
        <li key={n} value={n}><span className="dr-lines__n" aria-hidden="true">{n}</span><span className="dr-lines__t"><Highlight text={l} tokens={tokens} /></span></li>
      ))}
    </ol>
  );
}

function RowDetails({ view, row, block }: { view: DataRoomView; row: DataRoomRow; block: DataRoomBlock }) {
  const docOf = (p: string) => view.caseDocs.find((d) => d.path === p)!;
  return (
    <>
      <h4 className="dr-d__h">Letter text</h4>
      <p className="dr-d__text">{block.text}</p>

      <h4 className="dr-d__h">Policy</h4>
      {row.policy.kind === 'sections' && row.policy.sectionIds.map((id, i) => {
        const link = block.links.sections.find((s) => s.id === id);
        return (
          <div key={id} className="dr-d__sec">
            <p className="dr-d__secid">
              <span className="mono">{view.chosenPolicyId} section {id}</span>
              {link?.status && <Chip tone={link.status === 'met' ? 'green' : link.status === 'unmet' ? 'red' : 'amber'}>{link.status}</Chip>}
              {link?.evidence && <span className="muted small">evidence in decision: <span className="mono">{link.evidence}</span></span>}
            </p>
            <p className="dr-d__text">{row.policy.texts[i]}</p>
          </div>
        );
      })}
      {row.policy.kind === 'policy' && <p className="dr-d__text">This sentence names the policy that applies: {view.chosenPolicyId}. It does not point to a section.</p>}
      {row.policy.kind === 'none' && <p className="muted">No policy link found for this sentence.</p>}

      <h4 className="dr-d__h">Case evidence</h4>
      {row.evidence.length === 0 && <p className="muted">No case document is cited or matched for this sentence.</p>}
      {row.evidence.map((e) => {
        const d = docOf(e.file);
        return (
          <div key={e.file} className="dr-d__ev">
            <p className="dr-d__secid">
              <span className="dr-badge dr-badge--amber">{d.number}</span>
              <span className="mono">{e.file}</span>
              <Chip tone="amber">{e.via === 'cited' ? 'cited' : 'matched'}</Chip>
              {e.tokens.length > 0 && <span className="muted small">values: {[...new Set(e.tokens)].join(', ')}</span>}
            </p>
            {e.excerptFound && e.line ? <Lines doc={d} tokens={e.tokens} only={[e.line]} /> : <p className="muted">No line of this file overlaps the sentence.</p>}
          </div>
        );
      })}

      {block.links.flags.length > 0 && (
        <>
          <h4 className="dr-d__h">Flags</h4>
          {block.links.flags.map((f) => (
            <div key={f.id} className="dr-d__ev">
              <p className="dr-d__secid"><span className="mono">{f.id}</span><Chip tone="red">{f.severity}, upheld</Chip></p>
              <ul className="dr-d__reasons">{f.reasons.map((r, i) => <li key={i}>{r}</li>)}</ul>
            </div>
          ))}
        </>
      )}
    </>
  );
}

export function Details({ view, sel, onClear }: { view: DataRoomView; sel: Selection; onClear: () => void }) {
  let body: ReactNode = <p className="muted">Select a document, a policy, a matching card or a letter sentence to see the text behind it.</p>;
  if (sel?.type === 'row') {
    const row = view.rows.find((r) => r.blockId === sel.id);
    const block = view.blocks.find((b) => b.id === sel.id);
    if (row && block) body = <RowDetails view={view} row={row} block={block} />;
  } else if (sel?.type === 'doc') {
    const d = view.caseDocs.find((x) => x.path === sel.path);
    if (d) {
      const tokens = view.rows.flatMap((r) => r.evidence.filter((e) => e.file === d.path).flatMap((e) => e.tokens));
      body = (
        <>
          <p className="dr-d__secid"><span className="dr-badge dr-badge--amber">{d.number}</span><span className="mono">{d.path}</span><span className="muted small">{d.descriptor}, {openedLabel(d.opened)}</span></p>
          <div className="dr-d__scroll" tabIndex={0} role="region" aria-label={`Full text of ${d.path}`}><Lines doc={d} tokens={tokens} /></div>
        </>
      );
    }
  } else if (sel?.type === 'policy') {
    body = (
      <>
        <p className="dr-d__secid"><span className="dr-badge dr-badge--violet">P</span><span className="mono">{view.chosenPolicyId}</span></p>
        {view.chosenSections.map((s) => (
          <div key={s.id} className="dr-d__sec"><p className="dr-d__secid mono">Section {s.id}</p><p className="dr-d__text">{s.text}</p></div>
        ))}
      </>
    );
  }
  return (
    <section className="dr-details" aria-label="Details of the selection">
      <div className="dr-details__head">
        <h3 className="dr-d__title">Details</h3>
        {sel && <button type="button" className="btn btn--small" onClick={onClear}>Clear selection</button>}
      </div>
      {body}
    </section>
  );
}
