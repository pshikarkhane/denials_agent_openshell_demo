// Selection and chain logic for the Data room, kept free of React and the DOM
// so it can be tested directly.
import type { DataRoomRow, DataRoomView } from '../../data/types';

export type Selection =
  | { type: 'doc'; path: string }
  | { type: 'policy' }
  | { type: 'row'; id: string }
  | null;

export type ConnectorKind = 'doc-row' | 'policy-row' | 'row-block';

export interface Connector {
  kind: ConnectorKind;
  /** doc path, "policy", or a block id */
  from: string;
  /** block id */
  to: string;
}

export interface Chain {
  docs: Set<string>;
  rows: Set<string>;
  policy: boolean;
  connectors: Connector[];
}

export const hasPolicyZone = (r: DataRoomRow) => r.policy.kind !== 'none';

export function sameSelection(a: Selection, b: Selection): boolean {
  if (!a || !b) return a === b;
  if (a.type !== b.type) return false;
  if (a.type === 'doc') return a.path === (b as { path: string }).path;
  if (a.type === 'row') return a.id === (b as { id: string }).id;
  return true;
}

/** Selecting the selected item again clears it. */
export const toggle = (cur: Selection, next: Exclude<Selection, null>): Selection => (sameSelection(cur, next) ? null : next);

/** The first row with both a policy link and a cited file. */
export function defaultSelection(view: DataRoomView): Selection {
  const row = view.rows.find((r) => hasPolicyZone(r) && r.evidence.some((e) => e.via === 'cited'));
  return row ? { type: 'row', id: row.blockId } : null;
}

export function chainFor(view: DataRoomView, sel: Selection): Chain {
  const chain: Chain = { docs: new Set(), rows: new Set(), policy: false, connectors: [] };
  if (!sel) return chain;
  const addRow = (r: DataRoomRow) => {
    chain.rows.add(r.blockId);
    chain.connectors.push({ kind: 'row-block', from: r.blockId, to: r.blockId });
  };
  if (sel.type === 'doc') {
    chain.docs.add(sel.path);
    for (const r of view.rows) {
      if (!r.evidence.some((e) => e.file === sel.path)) continue;
      chain.connectors.push({ kind: 'doc-row', from: sel.path, to: r.blockId });
      addRow(r);
    }
  } else if (sel.type === 'policy') {
    chain.policy = true;
    for (const r of view.rows) {
      if (!hasPolicyZone(r)) continue;
      chain.connectors.push({ kind: 'policy-row', from: 'policy', to: r.blockId });
      addRow(r);
    }
  } else {
    const r = view.rows.find((x) => x.blockId === sel.id);
    if (r) {
      for (const e of r.evidence) {
        chain.docs.add(e.file);
        chain.connectors.push({ kind: 'doc-row', from: e.file, to: r.blockId });
      }
      if (hasPolicyZone(r)) {
        chain.policy = true;
        chain.connectors.push({ kind: 'policy-row', from: 'policy', to: r.blockId });
      }
      addRow(r);
    }
  }
  return chain;
}

export const HINT = 'Read from left to right: documents, then matching, then the letter. Click a document, row or sentence to trace its links.';

export function statusLine(view: DataRoomView, sel: Selection): string {
  if (!sel) return HINT;
  if (sel.type === 'policy') return `${view.chosenPolicyId} was chosen by payer, service and denial code.`;
  if (sel.type === 'doc') {
    const doc = view.caseDocs.find((d) => d.path === sel.path);
    const n = view.rows.filter((r) => r.evidence.some((e) => e.file === sel.path)).length;
    if (n > 0) return `${sel.path} supports ${n} part${n === 1 ? '' : 's'} of the letter.`;
    if (doc?.opened) return `${sel.path} was read but not cited in this letter.`;
    return `${sel.path} was not used in this letter.`;
  }
  const row = view.rows.find((r) => r.blockId === sel.id);
  if (!row) return HINT;
  const files = row.evidence.map((e) => e.file);
  const built = files.length ? `is built from ${files.join(', ')}` : 'has no case document link';
  const pol =
    row.policy.kind === 'sections' ? ` and matched to policy section ${row.policy.sectionIds.join(', ')}`
    : row.policy.kind === 'policy' ? ` and matched to policy ${view.chosenPolicyId}`
    : '';
  return `${row.title} ${built}${pol}.`;
}

export type DocUse = 'cited' | 'read' | 'matched' | 'unused';

export function docUse(d: { citedBy: string[]; matchedBy: string[]; opened: boolean | null }): DocUse {
  if (d.citedBy.length) return 'cited';
  if (d.opened) return 'read';
  if (d.matchedBy.length) return 'matched';
  return 'unused';
}

export const USE_LABEL: Record<DocUse, string> = {
  cited: '',
  read: 'Read, not cited',
  matched: 'Matched, not cited',
  unused: 'Not used',
};

export function openedLabel(opened: boolean | null): string {
  return opened === null ? 'pasted into the prompt' : opened ? 'opened by a tool' : 'no trace of being opened';
}
