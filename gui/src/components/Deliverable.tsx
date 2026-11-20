import type { ReactNode } from 'react';
import type { LocatedFlag } from '../lib/quotes';

// A small markdown view for the deliverables (headings, bullets, paragraphs,
// **bold**, `code`) that keeps raw-text offsets so flag quotes can be marked in
// place, and turns each "(source: ...)" citation into a pill.

interface Mark {
  start: number;
  end: number;
  id: string;
}

interface Node {
  kind: 'text' | 'bold' | 'code' | 'pill';
  text: string;
  /** Raw offset of text[0]. */
  at: number;
}

const INLINE = /\*\*(.+?)\*\*|`([^`]+)`|\((?:sources?):\s*([^)]*)\)/gi;

function tokenize(line: string, offset: number): Node[] {
  const out: Node[] = [];
  let last = 0;
  for (const m of line.matchAll(INLINE)) {
    const i = m.index ?? 0;
    if (i > last) out.push({ kind: 'text', text: line.slice(last, i), at: offset + last });
    if (m[1] !== undefined) out.push({ kind: 'bold', text: m[1], at: offset + i + 2 });
    else if (m[2] !== undefined) out.push({ kind: 'code', text: m[2], at: offset + i + 1 });
    else out.push({ kind: 'pill', text: m[0], at: offset + i });
    last = i + m[0].length;
  }
  if (last < line.length) out.push({ kind: 'text', text: line.slice(last), at: offset + last });
  return out;
}

function markText(text: string, at: number, marks: Mark[], key: string): ReactNode[] {
  const cuts = new Set([0, text.length]);
  for (const m of marks) {
    for (const p of [m.start - at, m.end - at]) if (p > 0 && p < text.length) cuts.add(p);
  }
  const points = [...cuts].sort((a, b) => a - b);
  const out: ReactNode[] = [];
  for (let i = 0; i < points.length - 1; i++) {
    const piece = text.slice(points[i], points[i + 1]);
    const pos = at + points[i];
    const hit = marks.find((m) => pos >= m.start && pos < m.end);
    out.push(
      hit ? (
        <mark key={`${key}-${i}`} className="hl hl--material" data-flag={hit.id}>
          {piece}
          {pos + piece.length === hit.end ? <sup className="hl__id">{hit.id}</sup> : null}
        </mark>
      ) : (
        piece
      ),
    );
  }
  return out;
}

function renderInline(line: string, offset: number, marks: Mark[], key: string): ReactNode[] {
  return tokenize(line, offset).map((n, i) => {
    const k = `${key}-${i}`;
    const end = n.at + n.text.length;
    const overlap = marks.filter((m) => m.start < end && m.end > n.at);
    if (n.kind === 'pill') {
      const body = n.text.replace(/^\(\s*/, '').replace(/\s*\)$/, '');
      const pill = <span className="cite">{body}</span>;
      return overlap.length ? (
        <mark key={k} className="hl hl--material" data-flag={overlap[0].id}>{pill}<sup className="hl__id">{overlap[0].id}</sup></mark>
      ) : (
        <span key={k}>{pill}</span>
      );
    }
    const inner = markText(n.text, n.at, overlap, k);
    if (n.kind === 'bold') return <strong key={k}>{inner}</strong>;
    if (n.kind === 'code') return <code key={k}>{inner}</code>;
    return <span key={k}>{inner}</span>;
  });
}

export function Deliverable({ markdown, flags }: { markdown: string; flags: LocatedFlag[] }) {
  const marks: Mark[] = flags.flatMap((f) => (f.range ? [{ ...f.range, id: f.flag.id }] : []));
  const blocks: ReactNode[] = [];
  let para: ReactNode[] = [];
  let offset = 0;
  const flush = (key: string) => {
    if (para.length) blocks.push(<p key={key}>{para}</p>);
    para = [];
  };

  markdown.split('\n').forEach((line, idx) => {
    const key = `l${idx}`;
    const heading = /^(#{1,6})\s+/.exec(line);
    const bullet = /^\s*[-*]\s+/.exec(line);
    if (!line.trim()) {
      flush(`p${idx}`);
    } else if (heading) {
      flush(`p${idx}`);
      const Tag = `h${Math.min(heading[1].length + 2, 6)}` as 'h3';
      blocks.push(<Tag key={key}>{renderInline(line.slice(heading[0].length), offset + heading[0].length, marks, key)}</Tag>);
    } else if (bullet) {
      flush(`p${idx}`);
      blocks.push(
        <ul key={key}><li>{renderInline(line.slice(bullet[0].length), offset + bullet[0].length, marks, key)}</li></ul>,
      );
    } else {
      if (para.length) para.push(<br key={`${key}-br`} />);
      para.push(...renderInline(line, offset, marks, key));
    }
    offset += line.length + 1;
  });
  flush('end');
  // Focusable so the scrolling box can be read with the keyboard.
  return <div className="doc" tabIndex={0} role="region" aria-label="Deliverable text">{blocks}</div>;
}
