/**
 * Dashboard Page - Main overview with real-time metrics
 * Inspired by Grafana design
 */
import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Activity, Server, AlertCircle, CheckCircle, Clock } from 'lucide-react';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { dashboardApi, nodesApi, alertsApi, actionsApi } from '../api/services';
import { useWebSocket } from '../hooks/useWebSocket';
import { useAuthStore } from '../store/authStore';
import { format } from 'date-fns';

const Dashboard: React.FC = () => {
  const { permissions } = useAuthStore();
  const { lastMessage, isConnected } = useWebSocket();
  const [selectedNode, setSelectedNode] = useState<number | null>(null);
  const [metricsHistory, setMetricsHistory] = useState<any[]>([]);

  // Fetch dashboard stats
  const { data: stats, refetch: refetchStats } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: dashboardApi.getStats,
    refetchInterval: 30000, // Refresh every 30s
  });

  // Fetch nodes
  const { data: nodes } = useQuery({
    queryKey: ['nodes'],
    queryFn: nodesApi.getAll,
  });

  // Fetch active alerts
  const { data: alerts } = useQuery({
    queryKey: ['active-alerts'],
    queryFn: () => alertsApi.getAll({ is_resolved: false, limit: 10 }),
  });

  // Fetch recent actions
  const { data: recentActions } = useQuery({
    queryKey: ['recent-actions'],
    queryFn: () => actionsApi.getAll({ limit: 10 }),
  });

  // Handle WebSocket updates
  useEffect(() => {
    if (lastMessage?.type === 'metrics') {
      const data = lastMessage.data;
      setMetricsHistory((prev) => [
        ...prev.slice(-59), // Keep last 60 points (5 minutes at 5s interval)
        {
          timestamp: new Date().toLocaleTimeString(),
          cpu: data.cpu_percent,
          memory: data.memory_percent,
          disk: data.disk_percent,
        },
      ]);
      refetchStats();
    }
  }, [lastMessage]);

  const getMetricColor = (value: number, warning: number, critical: number) => {
    if (value >= critical) return '#ef4444';
    if (value >= warning) return '#f59e0b';
    return '#10b981';
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
          <p className="text-gray-600 dark:text-gray-400">Real-time VPS monitoring overview</p>
        </div>
        <div className="flex items-center space-x-2">
          <div className={`flex items-center space-x-2 px-3 py-2 rounded-lg ${
            isConnected ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
          }`}>
            <div className={`w-2 h-2 rounded-full ${
              isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
            }`} />
            <span className="text-sm font-medium">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard
          title="Total Nodes"
          value={stats?.total_nodes || 0}
          subtitle={`${stats?.active_nodes || 0} active`}
          icon={<Server className="w-5 h-5" />}
          color="blue"
        />
        <StatsCard
          title="Containers"
          value={stats?.total_containers || 0}
          subtitle={`${stats?.running_containers || 0} running`}
          icon={<Activity className="w-5 h-5" />}
          color="green"
        />
        <StatsCard
          title="Active Alerts"
          value={stats?.active_alerts || 0}
          subtitle={`${stats?.critical_alerts || 0} critical`}
          icon={<AlertCircle className="w-5 h-5" />}
          color="red"
        />
        <StatsCard
          title="Actions (1h)"
          value={stats?.actions_last_hour || 0}
          subtitle="Automated actions"
          icon={<Clock className="w-5 h-5" />}
          color="purple"
        />
      </div>

      {/* Main Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* CPU Chart */}
        <ChartCard title="CPU Usage" color="#3b82f6">
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={metricsHistory}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="timestamp" stroke="#6b7280" fontSize={12} />
              <YAxis stroke="#6b7280" fontSize={12} domain={[0, 100]} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px' }}
                formatter={(value: number) => `${value.toFixed(1)}%`}
              />
              <Area 
                type="monotone" 
                dataKey="cpu" 
                stroke="#3b82f6" 
                fill="#3b82f6" 
                fillOpacity={0.2}
                name="CPU"
              />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Memory Chart */}
        <ChartCard title="Memory Usage" color="#10b981">
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart data={metricsHistory}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis dataKey="timestamp" stroke="#6b7280" fontSize={12} />
              <YAxis stroke="#6b7280" fontSize={12} domain={[0, 100]} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px' }}
                formatter={(value: number) => `${value.toFixed(1)}%`}
              />
              <Area 
                type="monotone" 
                dataKey="memory" 
                stroke="#10b981" 
                fill="#10b981" 
                fillOpacity={0.2}
                name="Memory"
              />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Disk Usage Chart (Full Width) */}
      <ChartCard title="Disk Usage" color="#f59e0b">
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={metricsHistory}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="timestamp" stroke="#6b7280" fontSize={12} />
            <YAxis stroke="#6b7280" fontSize={12} domain={[0, 100]} />
            <Tooltip 
              contentStyle={{ backgroundColor: '#fff', border: '1px solid #e5e7eb', borderRadius: '8px' }}
              formatter={(value: number) => `${value.toFixed(1)}%`}
            />
            <Legend />
            <Line 
              type="monotone" 
              dataKey="disk" 
              stroke="#f59e0b" 
              strokeWidth={2}
              dot={false}
              name="Disk"
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* Alerts and Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Alerts */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Active Alerts</h3>
          <div className="space-y-3">
            {alerts && alerts.length > 0 ? (
              alerts.map((alert: any) => (
                <AlertItem key={alert.id} alert={alert} />
              ))
            ) : (
              <div className="flex items-center justify-center py-8 text-gray-500">
                <CheckCircle className="w-5 h-5 mr-2" />
                <span>No active alerts</span>
              </div>
            )}
          </div>
        </div>

        {/* Recent Actions */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4 text-gray-900 dark:text-white">Recent Actions</h3>
          <div className="space-y-3">
            {recentActions && recentActions.length > 0 ? (
              recentActions.map((action: any) => (
                <ActionItem key={action.id} action={action} />
              ))
            ) : (
              <div className="flex items-center justify-center py-8 text-gray-500">
                <span>No recent actions</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// Stats Card Component
const StatsCard: React.FC<{
  title: string;
  value: number;
  subtitle: string;
  icon: React.ReactNode;
  color: string;
}> = ({ title, value, subtitle, icon, color }) => {
  const colorClasses = {
    blue: 'bg-blue-100 text-blue-600',
    green: 'bg-green-100 text-green-600',
    red: 'bg-red-100 text-red-600',
    purple: 'bg-purple-100 text-purple-600',
  }[color];

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-600 dark:text-gray-400">{title}</p>
          <p className="text-3xl font-bold text-gray-900 dark:text-white mt-1">{value}</p>
          <p className="text-xs text-gray-500 mt-1">{subtitle}</p>
        </div>
        <div className={`p-3 rounded-lg ${colorClasses}`}>
          {icon}
        </div>
      </div>
    </div>
  );
};

// Chart Card Component
const ChartCard: React.FC<{
  title: string;
  color: string;
  children: React.ReactNode;
}> = ({ title, color, children }) => (
  <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
    <div className="flex items-center space-x-2 mb-4">
      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{title}</h3>
    </div>
    {children}
  </div>
);

// Alert Item Component
const AlertItem: React.FC<{ alert: any }> = ({ alert }) => {
  const severityColors = {
    critical: 'bg-red-100 text-red-700 border-red-200',
    warning: 'bg-yellow-100 text-yellow-700 border-yellow-200',
    info: 'bg-blue-100 text-blue-700 border-blue-200',
  };

  return (
    <div className={`p-3 border-l-4 rounded ${severityColors[alert.severity as keyof typeof severityColors]}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="font-medium text-sm">{alert.title}</p>
          <p className="text-xs mt-1 opacity-80">{alert.message}</p>
          <p className="text-xs mt-1 opacity-60">{format(new Date(alert.created_at), 'HH:mm:ss')}</p>
        </div>
      </div>
    </div>
  );
};

// Action Item Component
const ActionItem: React.FC<{ action: any }> = ({ action }) => {
  const statusIcons = {
    success: <CheckCircle className="w-4 h-4 text-green-500" />,
    failed: <AlertCircle className="w-4 h-4 text-red-500" />,
    pending: <Clock className="w-4 h-4 text-yellow-500" />,
  };

  return (
    <div className="flex items-start space-x-3 p-3 hover:bg-gray-50 dark:hover:bg-gray-700 rounded">
      {statusIcons[action.status as keyof typeof statusIcons]}
      <div className="flex-1">
        <p className="text-sm font-medium text-gray-900 dark:text-white">{action.action_type}</p>
        <p className="text-xs text-gray-600 dark:text-gray-400">{action.reason || 'No reason provided'}</p>
        <p className="text-xs text-gray-500 mt-1">{format(new Date(action.created_at), 'HH:mm:ss')}</p>
      </div>
    </div>
  );
};

export default Dashboard;
