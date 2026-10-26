import { useEffect, useRef, useState } from "react";
import { request } from "./api";

export function useResource(path, interval = 0) {
  const [state, setState] = useState({ data: null, error: "", loading: true });
  const [revision, setRevision] = useState(0);
  const latestPath = useRef(path);
  useEffect(() => {
    latestPath.current = path;
    let active = true;
    let timer;
    const controller = new AbortController();
    async function fetchNext() {
      try {
        const data = await request(path, { signal: controller.signal });
        if (active) setState({ data, error: "", loading: false });
      } catch (error) {
        if (active && error.name !== "AbortError") {
          setState((previous) => ({
            ...previous,
            error: error.message,
            loading: false,
          }));
        }
      } finally {
        if (active && interval) timer = setTimeout(fetchNext, interval);
      }
    }
    fetchNext();
    return () => {
      active = false;
      controller.abort();
      clearTimeout(timer);
    };
  }, [path, interval, revision]);
  return { ...state, refresh: () => setRevision((value) => value + 1) };
}
