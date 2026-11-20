import type { ReactNode } from 'react';

// Inline 20px stroke icons (no emoji, no icon library).
const wrap = (children: ReactNode) => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
    {children}
  </svg>
);

export const IconCheck = () => wrap(<><circle cx="12" cy="12" r="9" /><path d="m8 12.5 3 3 5-6" /></>);
export const IconClock = () => wrap(<><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>);
export const IconShield = () => wrap(<><path d="M12 3 5 6v5c0 4.5 3 8 7 10 4-2 7-5.5 7-10V6l-7-3Z" /><path d="m9 12 2 2 4-4" /></>);
export const IconSwap = () => wrap(<><path d="M4 8h13l-3-3" /><path d="M20 16H7l3 3" /></>);
export const IconScore = () => wrap(<><path d="M5 20V10" /><path d="M12 20V4" /><path d="M19 20v-7" /></>);
export const IconPlay = () => wrap(<><rect x="3" y="4" width="18" height="16" rx="2" /><path d="m10 9 5 3-5 3V9Z" /></>);
