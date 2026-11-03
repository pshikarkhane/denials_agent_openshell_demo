import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import type { AttackRunView, DataIndex, DataRoomView, RunView } from './types';
import type { Metrics } from './metrics';
import type { Containment } from './containment';

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

export type DataRoomState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; view: DataRoomView };

/** Loads one data room file (public/data/dataroom/); pass null to skip. */
export function useDataRoom(file: string | null): DataRoomState {
  const [state, setState] = useState<DataRoomState>({ status: 'loading' });
  useEffect(() => {
    if (!file) return;
    let live = true;
    setState({ status: 'loading' });
    getJson<DataRoomView>(`dataroom/${file}`).then(
      (view) => live && setState({ status: 'ready', view }),
      (e: Error) => live && setState({ status: 'error', message: e.message }),
    );
    return () => {
      live = false;
    };
  }, [file]);
  return state;
}

export type ContainmentState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; data: Containment };

/** containment.json (Containment page, Home attack card). */
export function useContainment(): ContainmentState {
  const [state, setState] = useState<ContainmentState>({ status: 'loading' });
  useEffect(() => {
    let live = true;
    getJson<Containment>('containment.json').then(
      (data) => live && setState({ status: 'ready', data }),
      (e: Error) => live && setState({ status: 'error', message: e.message }),
    );
    return () => {
      live = false;
    };
  }, []);
  return state;
}

export type AttackRunState =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; run: AttackRunView };

/** One recorded attack run (public/data/containment/); pass null to skip. */
export function useAttackRun(file: string | null): AttackRunState {
  const [state, setState] = useState<AttackRunState>({ status: 'loading' });
  useEffect(() => {
    if (!file) return;
    let live = true;
    setState({ status: 'loading' });
    getJson<AttackRunView>(`containment/${file}`).then(
      (run) => live && setState({ status: 'ready', run }),
      (e: Error) => live && setState({ status: 'error', message: e.message }),
    );
    return () => {
      live = false;
    };
  }, [file]);
  return state;
}
