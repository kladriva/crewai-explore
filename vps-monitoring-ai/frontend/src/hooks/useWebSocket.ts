/**
 * WebSocket Hook for Real-Time Updates
 */
import { useEffect, useState, useRef } from 'react';
import { io, Socket } from 'socket.io-client';
import { useAuthStore } from '../store/authStore';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8001';

export interface WebSocketMessage {
  type: string;
  data: any;
}

export const useWebSocket = (nodeId?: number) => {
  const [isConnected, setIsConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<WebSocketMessage | null>(null);
  const socketRef = useRef<Socket | null>(null);
  const { token } = useAuthStore();

  useEffect(() => {
    if (!token) return;

    // Connect to WebSocket
    const socket = io(WS_URL, {
      auth: {
        token,
      },
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    socketRef.current = socket;

    socket.on('connect', () => {
      console.log('WebSocket connected');
      setIsConnected(true);

      // Subscribe to specific node if provided
      if (nodeId) {
        socket.emit('subscribe', { node_id: nodeId });
      }
    });

    socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
      setIsConnected(false);
    });

    socket.on('metrics', (data) => {
      setLastMessage({ type: 'metrics', data });
    });

    socket.on('alert', (data) => {
      setLastMessage({ type: 'alert', data });
    });

    socket.on('action', (data) => {
      setLastMessage({ type: 'action', data });
    });

    socket.on('node_status', (data) => {
      setLastMessage({ type: 'node_status', data });
    });

    return () => {
      socket.disconnect();
    };
  }, [token, nodeId]);

  const subscribe = (nodeId: number) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('subscribe', { node_id: nodeId });
    }
  };

  const unsubscribe = (nodeId: number) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit('unsubscribe', { node_id: nodeId });
    }
  };

  return {
    isConnected,
    lastMessage,
    subscribe,
    unsubscribe,
  };
};
