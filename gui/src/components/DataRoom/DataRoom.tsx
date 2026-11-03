import { Fragment, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import type { DataRoomBlock, DataRoomDoc, DataRoomRow, DataRoomView } from '../../data/types';
import { Chip } from '../Chip';
import { Details } from './Details';
import {
  USE_LABEL,
  chainFor,
  defaultSelection,
  docUse,
  openedLabel,
  statusLine,
  toggle,
  type Connector,
  type Selection,
} from './selection';

export const CITE_NOTE = "Citing a file means the letter points to it. It does not verify the claim. 'Matched' means the same value appears in that file.";

const connKey = (c: Connector) => `${c.kind}:${c.from}:${c.to}`;

// ---------- column 1 ----------

function DocButton({ doc, selected, dim, onSelect, refFn }: { doc: DataRoomDoc; selected: boolean; dim: boolean; onSelect: () => void; refFn: (el: HTMLElement | null) => void }) {
  const use = docUse(doc);
  return (
    <button
      type="button"
      ref={refFn}
      className={`dr-item dr-item--amber${use === 'cited' ? '' : ' is-dashed'}${dim ? ' is-dim' : ''}`}
      aria-pressed={selected}
      data-doc={doc.path}
      data-use={use}
      title={`${doc.path}, ${doc.descriptor}: ${openedLabel(doc.opened)}`}
      onClick={onSelect}
    >
      <span className="dr-badge dr-badge--amber">{doc.number}</span>
      <span className="dr-item__body">
        <span className="dr-item__file mono">{doc.path}</span>
        <span className="dr-item__desc">{doc.descriptor}</span>
        <span className="dr-item__meta">{USE_LABEL[use] && <strong>{USE_LABEL[use]}. </strong>}<span className="dr-item__opened">{openedLabel(doc.opened)}</span></span>
      </span>
    </button>
  );
}

function Frame({ view, sel, chain, onSelect, setRef, open, setOpen }: {
  view: DataRoomView;
  sel: Selection;
  chain: ReturnType<typeof chainFor>;
  onSelect: (s: Exclude<Selection, null>) => void;
  setRef: (key: string) => (el: HTMLElement | null) => void;
  open: boolean;
  setOpen: (v: boolean) => void;
}) {
  const dimming = sel !== null;
  const chosen = view.policies.find((p) => p.status === 'chosen');
  const lookalikes = view.policies.filter((p) => p.status === 'lookalike');
  const others = view.policies.filter((p) => p.status === 'other');
  return (
    <div className="dr-frame">
      <button type="button" className="dr-frame__toggle" aria-expanded={open} aria-controls="dr-frame-body" onClick={() => setOpen(!open)}>
        {open ? 'Hide' : 'Show'} the data room ({view.caseDocs.length} documents, {view.policies.length} policies)
      </button>
      <div id="dr-frame-body" className={`dr-frame__body${open ? '' : ' is-collapsed'}`}>
        <h3 className="dr-group dr-group--amber">Case folder</h3>
        <ul className="dr-list">
          {view.caseDocs.map((d) => (
            <li key={d.path}>
              <DocButton
                doc={d}
                selected={sel?.type === 'doc' && sel.path === d.path}
                dim={dimming && !chain.docs.has(d.path)}
                onSelect={() => onSelect({ type: 'doc', path: d.path })}
                refFn={setRef(`doc:${d.path}`)}
              />
            </li>
          ))}
        </ul>
        <h3 className="dr-group dr-group--violet">Payer policies</h3>
        <ul className="dr-list">
          {chosen && (
            <li>
              <button
                type="button"
                ref={setRef('policy')}
                className={`dr-item dr-item--violet${dimming && !chain.policy ? ' is-dim' : ''}`}
                aria-pressed={sel?.type === 'policy'}
                data-policy={chosen.id}
                title={`${chosen.id}, ${chosen.title}`}
                onClick={() => onSelect({ type: 'policy' })}
              >
                <span className="dr-badge dr-badge--violet">P</span>
                <span className="dr-item__body">
                  <span className="dr-item__file mono">{chosen.id}</span>
                  <span className="dr-item__desc">{chosen.title}</span>
                  <span className="dr-item__meta"><strong>Chosen. </strong>{chosen.payer}, effective {chosen.effective}</span>
                </span>
              </button>
            </li>
          )}
          {lookalikes.map((p) => (
            <li key={p.id}>
              <div className="dr-item dr-item--violet is-dashed is-static" data-lookalike={p.id}>
                <span className="dr-badge dr-badge--ghost">L</span>
                <span className="dr-item__body">
                  <span className="dr-item__file mono">{p.id}</span>
                  <span className="dr-item__desc">{p.title}</span>
                  <span className="dr-item__meta"><strong>Look-alike, not chosen. </strong>{p.payer}, effective {p.effective}</span>
                </span>
              </div>
            </li>
          ))}
          {others.length > 0 && (
            <li>
              <div className="dr-item dr-item--violet is-dashed is-static" data-others={others.length}>
                <span className="dr-item__body"><span className="dr-item__desc">{others.length} other {others.length === 1 ? 'policy' : 'policies'}</span></span>
              </div>
            </li>
          )}
        </ul>
      </div>
    </div>
  );
}

// ---------- columns 2 and 3 ----------

function PolicyZone({ row, view }: { row: DataRoomRow; view: DataRoomView }) {
  const p = view.policies.find((x) => x.status === 'chosen');
  return (
    <span className="dr-zone dr-zone--policy" data-zone="policy">
      <span className="dr-chip dr-chip--violet">POLICY</span>
      {row.policy.kind === 'sections' && (
        <>
          <span className="dr-zone__head mono" title={`${view.chosenPolicyId} section ${row.policy.sectionIds.join(', ')}`}>
            <span className="dr-zone__pid">{view.chosenPolicyId} </span>section {row.policy.sectionIds.join(', ')}
          </span>
          <span className="dr-clamp" title={row.policy.texts.join('\n')}>{row.policy.texts[0]}</span>
        </>
      )}
      {row.policy.kind === 'policy' && (
        <>
          <span className="dr-zone__head mono" title={p?.title}>{view.chosenPolicyId}</span>
          <span className="dr-clamp" title={p?.title}>{p?.title}</span>
        </>
      )}
      {row.policy.kind === 'none' && <span className="dr-zone__none" title="No policy link found">No policy link found</span>}
    </span>
  );
}

function CaseZone({ row, view }: { row: DataRoomRow; view: DataRoomView }) {
  const num = (f: string) => view.caseDocs.find((d) => d.path === f)?.number;
  const cited = row.evidence.filter((e) => e.via === 'cited');
  const matched = row.evidence.filter((e) => e.via === 'matched');
  const shown = row.evidence.filter((e) => e.excerptFound).slice(0, 1);
  return (
    <span className="dr-zone dr-zone--case" data-zone="case">
      <span className="dr-chip dr-chip--amber">CASE</span>
      {row.evidence.length === 0 && <span className="dr-zone__none">No case document link found</span>}
      {cited.length > 0 && (
        <span className="dr-badges">Cited{cited.map((e) => <span key={e.file} className="dr-badge dr-badge--amber" title={e.file}>{num(e.file)}</span>)}</span>
      )}
      {matched.length > 0 && (
        <span className="dr-badges">Matched{matched.map((e) => <span key={e.file} className="dr-badge dr-badge--amber dr-badge--outline" title={e.file}>{num(e.file)}</span>)}</span>
      )}
      {shown.map((e) => (
        <span key={e.file} className="dr-clamp dr-excerpt" title={`${e.file} line ${e.line}: ${e.excerpt}`}>
          <span className="mono">{num(e.file)} L{e.line}</span> {e.excerpt}
        </span>
      ))}
    </span>
  );
}

function isUnlinked(b: DataRoomBlock) {
  const l = b.links;
  return !(l.cited.length || l.matched.length || l.sections.length || l.policy);
}

// ---------- the view ----------

export function DataRoom({ view, initial, showUnlinked = false }: { view: DataRoomView; initial?: Selection | 'default'; showUnlinked?: boolean }) {
  const [sel, setSel] = useState<Selection>(() => (initial === undefined || initial === 'default' ? defaultSelection(view) : initial));
  const [open, setOpen] = useState(false);
  const [showAll, setShowAll] = useState(showUnlinked);
  const [excerpts, setExcerpts] = useState(false);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const chain = useMemo(() => chainFor(view, sel), [view, sel]);
  const dimming = sel !== null;
  const gridRef = useRef<HTMLDivElement | null>(null);
  const refs = useRef(new Map<string, HTMLElement>());
  const [paths, setPaths] = useState<Record<string, string>>({});
  const [size, setSize] = useState({ w: 0, h: 0 });

  const setRef = useCallback(
    (key: string) => (el: HTMLElement | null) => {
      if (el) refs.current.set(key, el);
      else refs.current.delete(key);
    },
    [],
  );

  const measure = useCallback(() => {
    const grid = gridRef.current;
    if (!grid) return;
    const g = grid.getBoundingClientRect();
    // Hidden (narrow layout): nothing to draw.
    if (window.matchMedia?.('(max-width: 1099px)').matches) {
      setPaths({});
      return;
    }
    const rel = (el: HTMLElement, side: 'left' | 'right') => {
      const r = el.getBoundingClientRect();
      return { x: (side === 'right' ? r.right : r.left) - g.left + grid.scrollLeft, y: r.top + r.height / 2 - g.top + grid.scrollTop };
    };
    const next: Record<string, string> = {};
    for (const c of chain.connectors) {
      const fromEl = refs.current.get(c.kind === 'doc-row' ? `doc:${c.from}` : c.kind === 'policy-row' ? 'policy' : `match:${c.from}`);
      const toEl = refs.current.get(c.kind === 'doc-row' ? `case:${c.to}` : c.kind === 'policy-row' ? `policy:${c.to}` : `letter:${c.to}`);
      if (!fromEl || !toEl) continue;
      const a = rel(fromEl, 'right');
      const b = rel(toEl, 'left');
      const dx = Math.max(24, (b.x - a.x) / 2);
      next[connKey(c)] = `M${a.x.toFixed(1)} ${a.y.toFixed(1)} C${(a.x + dx).toFixed(1)} ${a.y.toFixed(1)} ${(b.x - dx).toFixed(1)} ${b.y.toFixed(1)} ${b.x.toFixed(1)} ${b.y.toFixed(1)}`;
    }
    setPaths(next);
    setSize({ w: grid.scrollWidth, h: grid.scrollHeight });
  }, [chain]);

  useLayoutEffect(() => {
    measure();
  }, [measure]);

  useEffect(() => {
    const grid = gridRef.current;
    if (!grid) return;
    const again = () => measure();
    const ro = typeof ResizeObserver === 'undefined' ? null : new ResizeObserver(again);
    ro?.observe(grid);
    window.addEventListener('resize', again);
    grid.addEventListener('scroll', again);
    document.fonts?.ready.then(again);
    return () => {
      ro?.disconnect();
      window.removeEventListener('resize', again);
      grid.removeEventListener('scroll', again);
    };
  }, [measure]);

  const select = (s: Exclude<Selection, null>) => setSel((cur) => toggle(cur, s));
  // Parts of the letter with no link at all (and no flag) are folded away so the diagram fits the screen.
  const pairs = view.rows.map((row, i) => ({ row, block: view.blocks[i] }));
  const visible = showAll ? pairs : pairs.filter(({ block }) => !isUnlinked(block) || block.links.flags.length > 0);
  const hiddenCount = pairs.length - pairs.filter(({ block }) => !isUnlinked(block) || block.links.flags.length > 0).length;
  const n = visible.length;

  // Opening the tab brings the diagram to the top of the screen; the diagram then fills the viewport.
  useEffect(() => {
    rootRef.current?.scrollIntoView?.({ block: 'start' });
  }, []);

  return (
    <div className={`dr${excerpts ? '' : ' dr--lean'}`} ref={rootRef}>
      <div className="dr-bar">
      <ul className="dr-legend" aria-label="Legend">
        <li><span className="dr-swatch dr-swatch--amber" aria-hidden="true" />Amber: case folder and facts</li>
        <li><span className="dr-swatch dr-swatch--violet" aria-hidden="true" />Violet: payer policies</li>
        <li><span className="dr-swatch dr-swatch--blue" aria-hidden="true" />Blue: the letter</li>
        <li><span className="dr-swatch dr-swatch--dashed" aria-hidden="true" />Dashed: read but not cited, or not chosen</li>
      </ul>

      <p className="dr-fold">
        <button type="button" className="btn btn--small" aria-pressed={excerpts} onClick={() => setExcerpts(!excerpts)} data-excerpts>
          {excerpts ? 'Hide excerpts' : 'Show excerpts'}
        </button>{' '}
      {(hiddenCount > 0 || showAll) && (
        <>
          <button type="button" className="btn btn--small" aria-pressed={showAll} onClick={() => setShowAll(!showAll)} data-fold>
            {showAll ? 'Show only the parts with links' : `Show all ${pairs.length} parts of the letter (${hiddenCount} have no link)`}
          </button>
        </>
      )}
      </p>
      </div>

      <p className="dr-status" role="status" aria-live="polite" data-hint={sel ? undefined : 'true'}>{statusLine(view, sel)}</p>

      <div className="dr-grid" ref={gridRef} style={{ ['--dr-rows' as string]: n }}>
        <div className="dr-colhead dr-colhead--amber" style={{ gridColumn: 1, gridRow: 1 }}><span className="dr-step">1 DATA ROOM</span></div>
        <div className="dr-colhead dr-colhead--violet" style={{ gridColumn: 2, gridRow: 1 }}><span className="dr-step">2 MATCHING</span></div>
        <div className="dr-colhead dr-colhead--blue" style={{ gridColumn: 3, gridRow: 1 }}><span className="dr-step">3 THE LETTER</span></div>

        <div className="dr-col1" style={{ gridColumn: 1, gridRow: `2 / span ${Math.max(n, 1)}` }}>
          <Frame view={view} sel={sel} chain={chain} onSelect={select} setRef={setRef} open={open} setOpen={setOpen} />
        </div>
        <div className="dr-letterpanel" aria-hidden="true" style={{ gridColumn: 3, gridRow: `2 / span ${Math.max(n, 1)}` }} />

        {visible.map(({ row, block }, i) => {
          const inChain = chain.rows.has(row.blockId);
          const dim = dimming && !inChain;
          const flagged = block.links.flags.length > 0;
          const selected = sel?.type === 'row' && sel.id === row.blockId;
          return (
            <Fragment key={row.blockId}>
              <button
                type="button"
                ref={setRef(`match:${row.blockId}`)}
                className={`dr-match${dim ? ' is-dim' : ''}`}
                style={{ gridColumn: 2, gridRow: i + 2 }}
                aria-pressed={selected}
                data-row={row.blockId}
                data-in-chain={inChain ? 'true' : 'false'}
                onClick={() => select({ type: 'row', id: row.blockId })}
              >
                <span className="dr-match__title">{row.title}</span>
                <span ref={setRef(`policy:${row.blockId}`)} className="dr-zonewrap"><PolicyZone row={row} view={view} /></span>
                <span ref={setRef(`case:${row.blockId}`)} className="dr-zonewrap"><CaseZone row={row} view={view} /></span>
              </button>
              <button
                type="button"
                ref={setRef(`letter:${row.blockId}`)}
                className={`dr-letter${dim ? ' is-dim' : ''}${block.kind === 'heading' ? ' is-heading' : ''}`}
                style={{ gridColumn: 3, gridRow: i + 2 }}
                aria-pressed={selected}
                data-block={block.id}
                data-in-chain={inChain ? 'true' : 'false'}
                onClick={() => select({ type: 'row', id: row.blockId })}
              >
                {(flagged || isUnlinked(block)) && (
                  <span className="dr-letter__tags">
                    {flagged && <Chip tone="red">FLAGGED</Chip>}
                    {isUnlinked(block) && <span className="dr-letter__none">No source or policy link found</span>}
                  </span>
                )}
                <span className="dr-letter__text" title={block.text}>{block.text}</span>
              </button>
            </Fragment>
          );
        })}

        <svg className="dr-overlay" aria-hidden="true" focusable="false" width={size.w || undefined} height={size.h || undefined} data-connectors={chain.connectors.length}>
          <defs>
            <marker id="dr-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
              <path d="M0 0 L10 5 L0 10 z" fill="var(--dr-blue-sel-border)" />
            </marker>
          </defs>
          {chain.connectors.map((c) => (
            <path
              key={connKey(c)}
              className={`dr-conn dr-conn--${c.kind === 'doc-row' ? 'amber' : c.kind === 'policy-row' ? 'violet' : 'blue'}`}
              data-connector={c.kind}
              d={paths[connKey(c)] ?? ''}
              fill="none"
              markerEnd={c.kind === 'row-block' ? 'url(#dr-arrow)' : undefined}
            />
          ))}
        </svg>
      </div>

      <Details view={view} sel={sel} onClear={() => setSel(null)} />

      <section className="dr-note" aria-label="How the policy is chosen">
        <h3 className="dr-note__title">How the policy is chosen</h3>
        <p>
          Policies are filtered on payer, service, denial code and effective date before they are ranked. A look-alike can share a near-identical title with the chosen policy and still fail one of those filters.
        </p>
        {view.consideredPolicyIds.length > 0 ? (
          <p>
            In this run the policy search returned {view.consideredPolicyIds.map((id) => <span key={id} className="mono dr-note__id">{id}</span>)} and the agent chose <span className="mono dr-note__id">{view.chosenPolicyId}</span>.
          </p>
        ) : (
          <p>This run has no policy search in its trace, so the considered policies are not shown. The chosen policy is <span className="mono dr-note__id">{view.chosenPolicyId}</span>.</p>
        )}
        {view.policies.filter((p) => p.status === 'lookalike').map((p) => {
          const chosen = view.policies.find((x) => x.status === 'chosen');
          return (
            <p key={p.id} className="dr-note__look">
              Look-alike <span className="mono dr-note__id">{p.id}</span> has the title "{p.title}", payer {p.payer}, effective {p.effective}
              {chosen ? ` (chosen: ${chosen.payer}, effective ${chosen.effective})` : ''}.
            </p>
          );
        })}
        <p className="dr-note__cite">{CITE_NOTE}</p>
        {view.withheld.length > 0 && <p className="muted small">Withheld from the GUI: {view.withheld.join(', ')}.</p>}
      </section>
      <p className="muted small dr-summary">
        {view.summary.linkedBlocks} of {view.summary.blocks} parts of the letter have at least one link; {view.summary.citedFiles} files cited, {view.summary.matchedFiles} matched, {view.summary.flags} flag{view.summary.flags === 1 ? '' : 's'}.
      </p>
    </div>
  );
}
