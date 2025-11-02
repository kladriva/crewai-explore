/**
 * TypeScript Type Definitions
 */

export enum UserRole {
  ADMIN = 'admin',
  OPERATOR = 'operator',
  VIEWER = 'viewer',
}

export enum AlertSeverity {
  INFO = 'info',
  WARNING = 'warning',
  CRITICAL = 'critical',
}

export enum ActionStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  SUCCESS = 'success',
  FAILED = 'failed',
  SKIPPED = 'skipped',
}

export interface User {
  id: number;
  username: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

export interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
}

export interface Node {
  id: number;
  name: string;
  ip_address: string;
  node_type: 'master' | 'slave';
  is_active: boolean;
  last_heartbeat: string | null;
  agent_version: string | null;
  os_type: string | null;
  os_version: string | null;
  created_at: string;
  updated_at: string;
}

export interface SystemMetrics {
  cpu_percent: number;
  memory_percent: number;
  memory_used_mb: number;
  memory_total_mb: number;
  disk_percent: number;
  disk_used_gb: number;
  disk_total_gb: number;
  timestamp: string;
}

export interface Container {
  id: number;
  node_id: number;
  container_id: string;
  name: string;
  image: string;
  status: string;
  ports: Record<string, any>;
  first_deployed: string | null;
  last_updated: string;
  is_monitored: boolean;
  // Runtime stats
  cpu_percent?: number;
  memory_percent?: number;
  memory_used_mb?: number;
  memory_limit_mb?: number;
  network_rx_mb?: number;
  network_tx_mb?: number;
}

export interface Action {
  id: number;
  node_id: number;
  container_id: number | null;
  action_type: string;
  status: ActionStatus;
  reason: string | null;
  agent_explanation: string | null;
  triggered_by: string | null;
  execution_time: number | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

export interface Alert {
  id: number;
  node_id: number;
  severity: AlertSeverity;
  title: string;
  message: string;
  metric_type: string | null;
  metric_value: number | null;
  threshold_value: number | null;
  is_resolved: boolean;
  resolved_at: string | null;
  notified_email: boolean;
  notified_telegram: boolean;
  created_at: string;
}

export interface AuditLog {
  id: number;
  user_id: number | null;
  action: string;
  resource_type: string | null;
  resource_id: number | null;
  details: Record<string, any> | null;
  ip_address: string | null;
  user_agent: string | null;
  status: string;
  created_at: string;
}

export interface MetricsTimeSeriesPoint {
  timestamp: string;
  cpu_percent: number;
  memory_percent: number;
  disk_percent: number;
}

export interface DashboardStats {
  total_nodes: number;
  active_nodes: number;
  total_containers: number;
  running_containers: number;
  active_alerts: number;
  critical_alerts: number;
  actions_last_hour: number;
}

// RBAC Permissions
export interface Permissions {
  canViewDashboard: boolean;
  canViewNodes: boolean;
  canManageNodes: boolean;
  canViewContainers: boolean;
  canManageContainers: boolean;
  canViewAlerts: boolean;
  canResolveAlerts: boolean;
  canViewActions: boolean;
  canExecuteActions: boolean;
  canViewUsers: boolean;
  canManageUsers: boolean;
  canViewAuditLogs: boolean;
  canViewSettings: boolean;
  canManageSettings: boolean;
}

export const getRolePermissions = (role: UserRole): Permissions => {
  const basePermissions: Permissions = {
    canViewDashboard: true,
    canViewNodes: true,
    canManageNodes: false,
    canViewContainers: true,
    canManageContainers: false,
    canViewAlerts: true,
    canResolveAlerts: false,
    canViewActions: true,
    canExecuteActions: false,
    canViewUsers: false,
    canManageUsers: false,
    canViewAuditLogs: false,
    canViewSettings: false,
    canManageSettings: false,
  };

  switch (role) {
    case UserRole.ADMIN:
      return {
        canViewDashboard: true,
        canViewNodes: true,
        canManageNodes: true,
        canViewContainers: true,
        canManageContainers: true,
        canViewAlerts: true,
        canResolveAlerts: true,
        canViewActions: true,
        canExecuteActions: true,
        canViewUsers: true,
        canManageUsers: true,
        canViewAuditLogs: true,
        canViewSettings: true,
        canManageSettings: true,
      };
    
    case UserRole.OPERATOR:
      return {
        ...basePermissions,
        canManageContainers: true,
        canResolveAlerts: true,
        canExecuteActions: true,
        canViewSettings: true,
      };
    
    case UserRole.VIEWER:
    default:
      return basePermissions;
  }
};
