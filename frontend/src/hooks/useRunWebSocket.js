/**
 * useRunWebSocket
 *
 * Manages the WebSocket connection for a live test execution.
 * The hook owns the socket lifecycle: open → configure → stream events → close.
 *
 * Returned interface:
 *   isRunning    boolean          – true while the socket is open
 *   events       WsEvent[]        – all events received so far (accumulated)
 *   sessionId    string|null      – run UUID from execution.started (= DB run_id)
 *   startRun     (config) => void – open socket and start execution
 *   stopWatching () => void       – close socket (server keeps executing)
 *
 * The backend sends JSON frames matching domain/events.py .to_dict().
 * Terminal frames are: type === 'done' | 'error' (custom wrapper)
 * and type === 'execution.completed' (domain event).
 *
 * After the socket closes we call onFinished(sessionId) so the parent can
 * invalidate run-history queries and show the completed run.
 */

import { useCallback, useEffect, useRef, useState } from 'react'
import { wsUrl } from '../api/client.js'

// How long the backend waits for a config message (per backend source: 1 s).
// We send immediately on open, so this is just documentation.
const CONFIG_SEND_TIMEOUT_MS = 900

/**
 * @param {string}   testCaseId
 * @param {Function} onFinished  Called with sessionId when the run ends
 */
export function useRunWebSocket(testCaseId, onFinished) {
  const socketRef   = useRef(/** @type {WebSocket|null} */ (null))
  const onFinishedRef = useRef(onFinished)

  // Keep the callback ref current without re-creating the hook
  useEffect(() => { onFinishedRef.current = onFinished }, [onFinished])

  const [isRunning,  setIsRunning]  = useState(false)
  const [events,     setEvents]     = useState(/** @type {WsEvent[]} */ ([]))
  const [sessionId,  setSessionId]  = useState(/** @type {string|null} */ (null))

  // ── close helper ────────────────────────────────────────────────────────────

  const closeSocket = useCallback(() => {
    if (socketRef.current) {
      socketRef.current.onclose = null // prevent our onclose from firing again
      socketRef.current.close()
      socketRef.current = null
    }
    setIsRunning(false)
  }, [])

  // ── cleanup on unmount ───────────────────────────────────────────────────────

  useEffect(() => closeSocket, [closeSocket])

  // ── startRun ─────────────────────────────────────────────────────────────────

  /**
   * Open the WebSocket and begin execution.
   *
   * @param {{ provider?: string, model?: string|null, headless?: boolean }} config
   */
  const startRun = useCallback((config = {}) => {
    if (socketRef.current) return // already running

    // Reset state for the new run
    setEvents([])
    setSessionId(null)
    setIsRunning(true)

    const socket = new WebSocket(wsUrl(testCaseId))
    socketRef.current = socket

    // ── onopen: send config within the backend's 1 s window ─────────────────
    socket.onopen = () => {
      const payload = {
        provider: config.provider ?? 'google',
        model:    config.model    ?? null,
        headless: config.headless ?? true,
      }
      socket.send(JSON.stringify(payload))
    }

    // ── onmessage: accumulate events, capture session_id ────────────────────
    socket.onmessage = (msgEvent) => {
      let frame
      try {
        frame = JSON.parse(msgEvent.data)
      } catch {
        // Non-JSON frame — shouldn't happen, but guard anyway
        console.warn('[ws] non-JSON frame:', msgEvent.data)
        return
      }

      setEvents((prev) => [...prev, frame])

      // Capture the run ID as soon as the server emits execution.started
      if (frame.type === 'execution.started' && frame.session_id) {
        setSessionId(frame.session_id)
      }

      // Terminal frames — close and notify parent
      if (frame.type === 'done' || frame.type === 'error') {
        const sid = frame.session_id ?? frame.type // fallback key
        closeSocket()
        onFinishedRef.current?.(sid)
      }
    }

    // ── onerror: surface to event feed ──────────────────────────────────────
    socket.onerror = () => {
      setEvents((prev) => [
        ...prev,
        {
          type:    'error',
          message: 'WebSocket connection error. Is the server running?',
          event_id: 'ws-err',
          timestamp: new Date().toISOString(),
        },
      ])
    }

    // ── onclose: clean up ────────────────────────────────────────────────────
    socket.onclose = (ev) => {
      socketRef.current = null
      setIsRunning(false)

      // Abnormal closure — inject a synthetic error frame for the feed
      if (ev.code !== 1000 && ev.code !== 1005) {
        const reason =
          ev.code === 4009 ? 'Test case is already running.' :
          ev.code === 4004 ? 'Test case not found.' :
          `Connection closed (code ${ev.code})${ev.reason ? ': ' + ev.reason : ''}.`

        setEvents((prev) => [
          ...prev,
          {
            type:    'error',
            message: reason,
            event_id: 'ws-close',
            timestamp: new Date().toISOString(),
          },
        ])
      }
    }
  }, [testCaseId, closeSocket])

  // ── stopWatching ─────────────────────────────────────────────────────────────
  //
  // Closes the socket locally, which triggers the backend disconnect handler
  // to abort the active test execution on the server.

  const stopWatching = useCallback(() => {
    closeSocket()
  }, [closeSocket])

  return { isRunning, events, sessionId, startRun, stopWatching }
}

/**
 * @typedef {{
 *   type: string,
 *   session_id?: string,
 *   event_id?: string,
 *   timestamp?: string,
 *   [key: string]: unknown
 * }} WsEvent
 */
