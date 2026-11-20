import type { ReactNode } from 'react';

export type Tone = 'neutral' | 'green' | 'red' | 'amber';

/** Status is always carried by the text too, never by color alone. */
export function Chip({ tone = 'neutral', children, title }: { tone?: Tone; children: ReactNode; title?: string }) {
  return <span className={`chip chip--${tone}`} title={title}>{children}</span>;
}

export const verdictTone = (v: 'PASS' | 'FAIL'): Tone => (v === 'PASS' ? 'green' : 'red');
