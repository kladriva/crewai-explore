/**
 * API Services
 * All API calls organized by domain
 */
import apiClient from './client';
import {
  User,
  Node,
  Container,
  Action,
  Alert,
  AuditLog,
  SystemMetrics,
  MetricsTimeSeriesPoint,
  DashboardStats,
} from '../types';

// ==================== Auth ====================
export const authApi = {
  login: async (username: string, password: string) => {
    const response = await apiClient.post('/auth/login', { username, password });
    return response.data;
  },

  logout: async () => {
    const response = await apiClient.post('/auth/logout');
    return response.data;
  },

  getCurrentUser: async (): Promise<User> => {
    const response = await apiClient.get('/auth/me');
    return response.data;
  },

  refreshToken: async () => {
    const response = await apiClient.post('/auth/refresh');
    return response.data;
  },
};

// ==================== Dashboard ====================
export const dashboardApi = {
  getStats: async (): Promise<DashboardStats> => {
    const response = await apiClient.get('/dashboard/stats');
    return response.data;
  },
};

// ==================== Nodes ====================
export const nodesApi = {
  getAll: async (): Promise<Node[]> => {
    const response = await apiClient.get('/nodes');
    return response.data;
  },

  getById: async (id: number): Promise<Node> => {
    const response = await apiClient.get(`/nodes/${id}`);
    return response.data;
  },

  create: async (data: Partial<Node>): Promise<Node> => {
    const response = await apiClient.post('/nodes', data);
    return response.data;
  },

  update: async (id: number, data: Partial<Node>): Promise<Node> => {
    const response = await apiClient.put(`/nodes/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/nodes/${id}`);
  },

  getMetrics: async (
    id: number,
    params?: { limit?: number; from?: string; to?: string }
  ): Promise<MetricsTimeSeriesPoint[]> => {
    const response = await apiClient.get(`/nodes/${id}/metrics`, { params });
    return response.data;
  },

  getCurrentMetrics: async (id: number): Promise<SystemMetrics> => {
    const response = await apiClient.get(`/nodes/${id}/metrics/current`);
    return response.data;
  },
};

// ==================== Containers ====================
export const containersApi = {
  getByNode: async (nodeId: number): Promise<Container[]> => {
    const response = await apiClient.get(`/nodes/${nodeId}/containers`);
    return response.data;
  },

  getById: async (id: number): Promise<Container> => {
    const response = await apiClient.get(`/containers/${id}`);
    return response.data;
  },

  start: async (id: number): Promise<void> => {
    await apiClient.post(`/containers/${id}/start`);
  },

  stop: async (id: number): Promise<void> => {
    await apiClient.post(`/containers/${id}/stop`);
  },

  restart: async (id: number): Promise<void> => {
    await apiClient.post(`/containers/${id}/restart`);
  },

  getLogs: async (id: number, params?: { tail?: number; follow?: boolean }): Promise<string> => {
    const response = await apiClient.get(`/containers/${id}/logs`, { params });
    return response.data;
  },

  updateMonitoring: async (id: number, isMonitored: boolean): Promise<Container> => {
    const response = await apiClient.patch(`/containers/${id}`, { is_monitored: isMonitored });
    return response.data;
  },
};

// ==================== Actions ====================
export const actionsApi = {
  getAll: async (params?: {
    node_id?: number;
    container_id?: number;
    limit?: number;
    offset?: number;
  }): Promise<Action[]> => {
    const response = await apiClient.get('/actions', { params });
    return response.data;
  },

  getById: async (id: number): Promise<Action> => {
    const response = await apiClient.get(`/actions/${id}`);
    return response.data;
  },

  execute: async (data: {
    node_id: number;
    container_id?: number;
    action_type: string;
    reason: string;
    dry_run?: boolean;
  }): Promise<Action> => {
    const response = await apiClient.post('/actions/execute', data);
    return response.data;
  },
};

// ==================== Alerts ====================
export const alertsApi = {
  getAll: async (params?: {
    node_id?: number;
    severity?: string;
    is_resolved?: boolean;
    limit?: number;
  }): Promise<Alert[]> => {
    const response = await apiClient.get('/alerts', { params });
    return response.data;
  },

  getById: async (id: number): Promise<Alert> => {
    const response = await apiClient.get(`/alerts/${id}`);
    return response.data;
  },

  resolve: async (id: number): Promise<Alert> => {
    const response = await apiClient.put(`/alerts/${id}/resolve`);
    return response.data;
  },
};

// ==================== Users ====================
export const usersApi = {
  getAll: async (): Promise<User[]> => {
    const response = await apiClient.get('/users');
    return response.data;
  },

  getById: async (id: number): Promise<User> => {
    const response = await apiClient.get(`/users/${id}`);
    return response.data;
  },

  create: async (data: {
    username: string;
    email: string;
    password: string;
    role: string;
  }): Promise<User> => {
    const response = await apiClient.post('/users', data);
    return response.data;
  },

  update: async (id: number, data: Partial<User>): Promise<User> => {
    const response = await apiClient.put(`/users/${id}`, data);
    return response.data;
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/users/${id}`);
  },
};

// ==================== Audit Logs ====================
export const auditApi = {
  getAll: async (params?: {
    user_id?: number;
    resource_type?: string;
    limit?: number;
  }): Promise<AuditLog[]> => {
    const response = await apiClient.get('/audit', { params });
    return response.data;
  },
};

// ==================== ML ====================
export const mlApi = {
  retrain: async (data?: { model_type?: string; node_ids?: number[] }) => {
    const response = await apiClient.post('/ml/train', data);
    return response.data;
  },

  getModels: async () => {
    const response = await apiClient.get('/ml/models');
    return response.data;
  },
};
