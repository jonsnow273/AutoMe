import { useEffect, useRef, useState, useCallback } from 'react';
import { io } from 'socket.io-client';
import api from '../utils/api';

const SOCKET_URL = 'http://localhost:8000';

export function useSocket() {
  const socketRef = useRef(null);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState(null);
  const listenersRef = useRef(new Map());

  useEffect(() => {
    const token = localStorage.getItem('autome_token');
    if (!token) return;

    socketRef.current = io(SOCKET_URL, {
      auth: { token },
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
    });

    const socket = socketRef.current;

    socket.on('connect', () => {
      console.log('Socket connected');
      setConnected(true);
      setError(null);
    });

    socket.on('disconnect', (reason) => {
      console.log('Socket disconnected:', reason);
      setConnected(false);
    });

    socket.on('connect_error', (err) => {
      console.error('Socket connection error:', err.message);
      setError(err.message);
      setConnected(false);
    });

    // Re-emit events to registered listeners
    socket.onAny((event, data) => {
      const callbacks = listenersRef.current.get(event);
      if (callbacks) {
        callbacks.forEach(cb => cb(data));
      }
    });

    return () => {
      socket.disconnect();
      socketRef.current = null;
    };
  }, []);

  const on = useCallback((event, callback) => {
    if (!listenersRef.current.has(event)) {
      listenersRef.current.set(event, new Set());
    }
    listenersRef.current.get(event).add(callback);

    return () => {
      const callbacks = listenersRef.current.get(event);
      if (callbacks) {
        callbacks.delete(callback);
      }
    };
  }, []);

  const off = useCallback((event, callback) => {
    const callbacks = listenersRef.current.get(event);
    if (callbacks) {
      callbacks.delete(callback);
    }
  }, []);

  const emit = useCallback((event, data) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit(event, data);
    }
  }, []);

  return { socket: socketRef.current, connected, error, on, off, emit };
}

// Specialized hook for message events
export function useMessageSocket() {
  const { on, off, connected } = useSocket();
  const [newMessage, setNewMessage] = useState(null);
  const [messageRead, setMessageRead] = useState(null);

  useEffect(() => {
    const unsubNew = on('new_message', (data) => {
      console.log('New message received:', data);
      setNewMessage(data);
    });

    const unsubRead = on('message_read', (data) => {
      setMessageRead(data);
    });

    return () => {
      unsubNew();
      unsubRead();
    };
  }, [on]);

  return { connected, newMessage, messageRead };
}