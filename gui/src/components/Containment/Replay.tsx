import { useEffect, useRef, useState } from 'react';

/** Play/pause and a scrubber over the merged timeline. No autoplay; position === total shows the final state. */
export function Replay({ total, pos, setPos }: { total: number; pos: number; setPos: (n: number) => void }) {
  const [playing, setPlaying] = useState(false);
  const posRef = useRef(pos);
  posRef.current = pos;

  useEffect(() => {
    if (!playing) return;
    const id = window.setInterval(() => {
      if (posRef.current >= total) {
        setPlaying(false);
        return;
      }
      setPos(posRef.current + 1);
    }, 90);
    return () => window.clearInterval(id);
  }, [playing, total, setPos]);

  const toggle = () => {
    if (playing) setPlaying(false);
    else {
      if (pos >= total) setPos(0);
      setPlaying(true);
    }
  };

  return (
    <section className="ct-panel ct-replay" aria-labelledby="ct-replay">
      <h3 id="ct-replay" className="ct-panel__h">Replay</h3>
      <div className="ct-replay__bar">
        <button type="button" className="btn" aria-pressed={playing} onClick={toggle}>{playing ? 'Pause' : 'Play'}</button>
        <label className="ct-replay__label" htmlFor="ct-scrub">Position in the time-ordered steps and audit events</label>
        <input
          id="ct-scrub"
          type="range"
          min={0}
          max={total}
          value={pos}
          onChange={(e) => {
            setPlaying(false);
            setPos(Number(e.target.value));
          }}
          aria-valuetext={pos >= total ? 'final state, all events shown' : `${pos} of ${total} events shown`}
        />
        <span className="mono small" aria-live="off">{pos >= total ? 'final state' : `${pos} / ${total}`}</span>
        <button type="button" className="btn btn--small" onClick={() => { setPlaying(false); setPos(total); }} disabled={pos >= total}>Show final state</button>
      </div>
    </section>
  );
}
