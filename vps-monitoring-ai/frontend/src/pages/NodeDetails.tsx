/**
 * Node Details Page
 * Shows metrics and containers for a specific node
 */
import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { nodesApi, containersApi } from '../api/services';
import { useAuthStore } from '../store/authStore';
import { useWebSocket } from '../hooks/useWebSocket';
import {
  Server,
  Activity,
  Play,
  Square,
  RotateCw,
  FileText,
  Eye,
  EyeOff,
} from 'lucide-react';
import { Container } from '../types';
import { format } from 'date-fns';
import { LineChart, Line, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts';

const NodeDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const nodeId = parseInt(id || '0');
  const { permissions } = useAuthStore();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'overview' | 'containers'>('overview');
  const { lastMessage } = useWebSocket(nodeId);
  const [metricsHistory, setMetricsHistory] = useState<any[]>([]);

  const { data: node } = useQuery({
    queryKey: ['node', nodeId],
    queryFn: () => nodesApi.getById(nodeId),
  });

  const { data: currentMetrics } = useQuery({
    queryKey: ['node-metrics', nodeId],
    queryFn: () => nodesApi.getCurrentMetrics(nodeId),
    refetchInterval: 5000,
  });

  const { data: containers } = useQuery({
    queryKey: ['containers', nodeId],
    queryFn: () => containersApi.getByNode(nodeId),
    refetchInterval: 10000,
  });

  // Update metrics history from WebSocket
  React.useEffect(() => {
    if (lastMessage?.type === 'metrics') {
      setMetricsHistory((prev) => [
        ...prev.slice(-119),
        {
          time: new Date().toLocaleTimeString(),
          cpu: lastMessage.data.cpu_percent,
          memory: lastMessage.data.memory_percent,
          disk: lastMessage.data.disk_percent,
        },
      ]);
    }
  }, [lastMessage]);

  const getMetricColor = (value: number, warning: number, critical: number) => {
    if (value >= critical) return 'text-red-600 bg-red-50';
    if (value >= warning) return 'text-yellow-600 bg-yellow-50';
    return 'text-green-600 bg-green-50';
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="p-3 bg-blue-100 text-blue-600 rounded-lg">
            <Server className="w-8 h-8" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">{node?.name}</h1>
            <p className="text-gray-600 dark:text-gray-400">{node?.ip_address}</p>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="flex space-x-8">
          <button
            onClick={() => setActiveTab('overview')}
            className={`py-4 px-1 border-b-2 font-medium text-sm transition ${
              activeTab === 'overview'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Overview
          </button>
          <button
            onClick={() => setActiveTab('containers')}
            className={`py-4 px-1 border-b-2 font-medium text-sm transition ${
              activeTab === 'containers'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Containers ({containers?.length || 0})
          </button>
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          {/* Metrics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <MetricCard
              title="CPU Usage"
              value={currentMetrics?.cpu_percent || 0}
              unit="%"
              color={getMetricColor(currentMetrics?.cpu_percent || 0, 70, 85)}
            />
            <MetricCard
              title="Memory Usage"
              value={currentMetrics?.memory_percent || 0}
              unit="%"
              color={getMetricColor(currentMetrics?.memory_percent || 0, 75, 90)}
            />
            <MetricCard
              title="Disk Usage"
              value={currentMetrics?.disk_percent || 0}
              unit="%"
              color={getMetricColor(currentMetrics?.disk_percent || 0, 80, 95)}
            />
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ChartCard title="CPU & Memory" data={metricsHistory} />
          </div>
        </div>
      )}

      {activeTab === 'containers' && (
        <div className="space-y-4">
          {containers && containers.length > 0 ? (
            containers.map((container: Container) => (
              <ContainerCard
                key={container.id}
                container={container}
                canManage={permissions.canManageContainers}
              />
            ))
          ) : (
            <div className="text-center py-12 bg-white dark:bg-gray-800 rounded-lg">
              <Activity className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600 dark:text-gray-400">No containers found</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

// Metric Card
const MetricCard: React.FC<{
  title: string;
  value: number;
  unit: string;
  color: string;
}> = ({ title, value, unit, color }) => (
  <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
    <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">{title}</p>
    <div className="flex items-baseline space-x-2">
      <span className="text-4xl font-bold text-gray-900 dark:text-white">
        {value.toFixed(1)}
      </span>
      <span className="text-xl text-gray-500">{unit}</span>
    </div>
    <div className={`mt-3 inline-block px-3 py-1 rounded-full text-xs font-medium ${color}`}>
      {value >= 85 ? 'Critical' : value >= 70 ? 'Warning' : 'Normal'}
    </div>
  </div>
);

// Chart Card
const ChartCard: React.FC<{ title: string; data: any[] }> = ({ title, data }) => (
  <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">{title}</h3>
    <ResponsiveContainer width="100%" height={200}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="time" stroke="#6b7280" fontSize={10} />
        <YAxis stroke="#6b7280" fontSize={10} domain={[0, 100]} />
        <Tooltip />
        <Line type="monotone" dataKey="cpu" stroke="#3b82f6" strokeWidth={2} dot={false} name="CPU" />
        <Line type="monotone" dataKey="memory" stroke="#10b981" strokeWidth={2} dot={false} name="Memory" />
      </LineChart>
    </ResponsiveContainer>
  </div>
);

// Container Card
const ContainerCard: React.FC<{
  container: Container;
  canManage: boolean;
}> = ({ container, canManage }) => {
  const queryClient = useQueryClient();
  const [showLogs, setShowLogs] = useState(false);

  const startMutation = useMutation({
    mutationFn: () => containersApi.start(container.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['containers'] }),
  });

  const stopMutation = useMutation({
    mutationFn: () => containersApi.stop(container.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['containers'] }),
  });

  const restartMutation = useMutation({
    mutationFn: () => containersApi.restart(container.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['containers'] }),
  });

  const isRunning = container.status === 'running';

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <div className="flex items-center space-x-3 mb-2">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              {container.name}
            </h3>
            <span className={`px-2 py-1 rounded text-xs font-medium ${
              isRunning ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
            }`}>
              {container.status}
            </span>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">{container.image}</p>
        </div>
        
        {/* Actions */}
        {canManage && (
          <div className="flex space-x-2">
            {!isRunning && (
              <button
                onClick={() => startMutation.mutate()}
                className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition"
                title="Start"
              >
                <Play className="w-4 h-4" />
              </button>
            )}
            {isRunning && (
              <>
                <button
                  onClick={() => stopMutation.mutate()}
                  className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition"
                  title="Stop"
                >
                  <Square className="w-4 h-4" />
                </button>
                <button
                  onClick={() => restartMutation.mutate()}
                  className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition"
                  title="Restart"
                >
                  <RotateCw className="w-4 h-4" />
                </button>
              </>
            )}
            <button
              onClick={() => setShowLogs(!showLogs)}
              className="p-2 text-gray-600 hover:bg-gray-50 rounded-lg transition"
              title="Logs"
            >
              <FileText className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-4 gap-4 text-sm">
        <div>
          <p className="text-gray-600 dark:text-gray-400">CPU</p>
          <p className="font-semibold text-gray-900 dark:text-white">
            {container.cpu_percent?.toFixed(1) || 0}%
          </p>
        </div>
        <div>
          <p className="text-gray-600 dark:text-gray-400">Memory</p>
          <p className="font-semibold text-gray-900 dark:text-white">
            {container.memory_percent?.toFixed(1) || 0}%
          </p>
        </div>
        <div>
          <p className="text-gray-600 dark:text-gray-400">Network RX</p>
          <p className="font-semibold text-gray-900 dark:text-white">
            {container.network_rx_mb?.toFixed(1) || 0} MB
          </p>
        </div>
        <div>
          <p className="text-gray-600 dark:text-gray-400">Network TX</p>
          <p className="font-semibold text-gray-900 dark:text-white">
            {container.network_tx_mb?.toFixed(1) || 0} MB
          </p>
        </div>
      </div>
    </div>
  );
};

export default NodeDetails;
