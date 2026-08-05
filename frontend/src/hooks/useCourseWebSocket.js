import { useEffect, useRef, useState } from 'react'
import { courseWebSocketUrl } from '../api/attainment'

/**
 * Opens a live-updates socket for one course and calls `onMessage` whenever
 * the backend broadcasts a recalculation. Reconnects with backoff if the
 * connection drops, since faculty may leave the dashboard open for hours.
 */
export function useCourseWebSocket(courseId, onMessage) {
  const [isConnected, setIsConnected] = useState(false)
  const onMessageRef = useRef(onMessage)
  onMessageRef.current = onMessage

  useEffect(() => {
    if (!courseId) return undefined

    let socket
    let reconnectTimer
    let cancelled = false
    let attempt = 0

    const connect = () => {
      socket = new WebSocket(courseWebSocketUrl(courseId))

      socket.onopen = () => {
        attempt = 0
        setIsConnected(true)
      }

      socket.onmessage = (event) => {
        try {
          onMessageRef.current?.(JSON.parse(event.data))
        } catch {
          // Ignore malformed frames rather than tearing down the connection.
        }
      }

      socket.onclose = () => {
        setIsConnected(false)
        if (cancelled) return
        const delay = Math.min(1000 * 2 ** attempt, 15000)
        attempt += 1
        reconnectTimer = setTimeout(connect, delay)
      }

      socket.onerror = () => {
        socket.close()
      }
    }

    connect()

    return () => {
      cancelled = true
      clearTimeout(reconnectTimer)
      socket?.close()
    }
  }, [courseId])

  return { isConnected }
}
