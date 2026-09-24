"use client";

import { useEffect, useState } from "react";

import { getScan, ScanApiError, type ScanStatusResponse } from "@/lib/scan/api";

const POLL_MS = 1500;
const TERMINAL = new Set(["completed", "failed", "cancelled"]);

type Session = {
  scan: ScanStatusResponse | null;
  error: string | null;
  listeners: Set<() => void>;
  timer: number | undefined;
  abort: AbortController | null;
};

const sessions = new Map<string, Session>();

function notify(session: Session) {
  session.listeners.forEach((listener) => listener());
}

function isAbort(caught: unknown) {
  return caught instanceof DOMException && caught.name === "AbortError";
}

async function load(scanId: string, session: Session) {
  session.abort?.abort();
  const abort = new AbortController();
  session.abort = abort;
  try {
    const next = await getScan(scanId, abort.signal);
    if (abort.signal.aborted) {
      return;
    }
    session.scan = next;
    session.error = null;
    notify(session);
    if (!TERMINAL.has(next.status)) {
      session.timer = window.setTimeout(() => {
        void load(scanId, session);
      }, POLL_MS);
    }
  } catch (caught) {
    if (abort.signal.aborted || isAbort(caught)) {
      return;
    }
    const message =
      caught instanceof ScanApiError ? caught.message : "Unable to analyze this website.";
    session.error = message;
    notify(session);
    if (!(caught instanceof ScanApiError && caught.code === "SCAN_NOT_FOUND")) {
      session.timer = window.setTimeout(() => {
        void load(scanId, session);
      }, POLL_MS);
    }
  }
}

export function useScanStatus(scanId: string) {
  const [scan, setScan] = useState<ScanStatusResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let session = sessions.get(scanId);
    if (!session) {
      session = { scan: null, error: null, listeners: new Set(), timer: undefined, abort: null };
      sessions.set(scanId, session);
      void load(scanId, session);
    }
    const onChange = () => {
      setScan(session!.scan);
      setError(session!.error);
    };
    session.listeners.add(onChange);
    onChange();
    return () => {
      session!.listeners.delete(onChange);
      if (session!.listeners.size === 0) {
        if (session!.timer !== undefined) {
          window.clearTimeout(session!.timer);
        }
        session!.abort?.abort();
        sessions.delete(scanId);
      }
    };
  }, [scanId]);

  return { scan, error };
}
