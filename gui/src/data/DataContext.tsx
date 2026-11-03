import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import type { DataIndex, RunView } from './types';
import type { Metrics } from './metrics';

export type IndexState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; index: DataIndex };

export const DataContext = createContext<IndexState>({ status: 'loading' });

export type MetricsState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; metrics: Metrics };

const base = () => import.meta.env.BASE_URL;

/** Cached mode only: the app reads from its own origin and nothing else. */
async function getJson<T>(file: string): Promise<T> {
  const res = await fetch(`${base()}data/${file}`);
  if (!res.ok) throw new Error(`${file}: HTTP ${res.status}`);
  return (await res.json()) as T;
}

export function DataProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<IndexState>({ status: 'loading' });
  useEffect(() => {
    let live = true;
    getJson<DataIndex>('index.json').then(
      (index) => live && setState({ status: 'ready', index }),
      (e: Error) => live && setState({ status: 'error', message: e.message }),
    );
    return () => {
      live = false;
    };
  }, []);
  return <DataContext.Provider value={state}>{children}</DataContext.Provider>;
}

export const useIndexState = () => useContext(DataContext);

/** metrics.json (Scorecard). Shape: scripts/build_metrics.mjs, typed in ./metrics.ts. */
export function useMetrics(): MetricsState {
  const [state, setState] = useState<MetricsState>({ status: 'loading' });
  useEffect(() => {
    let live = true;
    getJson<Metrics>('metrics.json').then(
      (metrics) => live && setState({ status: 'ready', metrics }),
      (e: Error) => live && setState({ status: 'error', message: e.message }),
    );
    return () => {
      live = false;
    };
  }, []);
  return state;
}

export type RunState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; run: RunView };

/** Loads one normalized run file; pass null to skip. */
export function useRun(file: string | null): RunState {
  const [state, setState] = useState<RunState>({ status: 'loading' });
  useEffect(() => {
    if (!file) return;
    let live = true;
    setState({ status: 'loading' });
    getJson<RunView>(file).then(
      (run) => live && setState({ status: 'ready', run }),
      (e: Error) => live && setState({ status: 'error', message: e.message }),
    );
    return () => {
      live = false;
    };
  }, [file]);
  return state;
}
