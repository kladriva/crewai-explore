/**
 * Nodes List Page
 */
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Server, Plus, Trash2, AlertCircle, CheckCircle, Circle } from 'lucide-react';
import { nodesApi } from '../api/services';
import { useAuthStore } from '../store/authStore';
import { Node } from '../types';
import { formatDistanceToNow } from 'date-fns';

const Nodes: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { permissions } = useAuthStore();
  const [showAddModal, setShowAddModal] = useState(false);

  const { data: nodes, isLoading } = useQuery({
    queryKey: ['nodes'],
    queryFn: nodesApi.getAll,
    refetchInterval: 30000,
  });

  const deleteMutation = useMutation({
    mutationFn: nodesApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['nodes'] });
    },
  });

  const handleDelete = async (id: number) => {
    if (window.confirm('Are you sure you want to delete this node?')) {
      await deleteMutation.mutateAsync(id);
    }
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Nodes</h1>
          <p className="text-gray-600 dark:text-gray-400">Manage your VPS nodes</p>
        </div>
        {permissions.canManageNodes && (
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition"
          >
            <Plus className="w-5 h-5" />
            <span>Add Node</span>
          </button>
        )}
      </div>

      {/* Nodes Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {nodes?.map((node: Node) => (
            <NodeCard
              key={node.id}
              node={node}
              onView={() => navigate(`/nodes/${node.id}`)}
              onDelete={permissions.canManageNodes ? () => handleDelete(node.id) : undefined}
            />
          ))}
        </div>
      )}

      {nodes && nodes.length === 0 && (
        <div className="text-center py-12">
          <Server className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-600 dark:text-gray-400">No nodes configured yet</p>
        </div>
      )}
    </div>
  );
};

// Node Card Component
const NodeCard: React.FC<{
  node: Node;
  onView: () => void;
  onDelete?: () => void;
}> = ({ node, onView, onDelete }) => {
  const isOnline = node.is_active && node.last_heartbeat;
  const lastSeen = node.last_heartbeat
    ? formatDistanceToNow(new Date(node.last_heartbeat), { addSuffix: true })
    : 'Never';

  return (
    <div className="bg-white dark:bg-gray-800 rounded-lg shadow hover:shadow-lg transition p-6">
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className={`p-2 rounded-lg ${
            isOnline ? 'bg-green-100 text-green-600' : 'bg-gray-100 text-gray-600'
          }`}>
            <Server className="w-6 h-6" />
          </div>
          <div>
            <h3 className="font-semibold text-gray-900 dark:text-white">{node.name}</h3>
            <p className="text-sm text-gray-500">{node.ip_address}</p>
          </div>
        </div>
        {onDelete && (
          <button
            onClick={onDelete}
            className="text-gray-400 hover:text-red-600 transition"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Status */}
      <div className="flex items-center space-x-2 mb-4">
        <Circle
          className={`w-3 h-3 ${
            isOnline ? 'fill-green-500 text-green-500' : 'fill-gray-400 text-gray-400'
          }`}
        />
        <span className={`text-sm font-medium ${
          isOnline ? 'text-green-600' : 'text-gray-600'
        }`}>
          {isOnline ? 'Online' : 'Offline'}
        </span>
      </div>

      {/* Info */}
      <div className="space-y-2 text-sm mb-4">
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">Type:</span>
          <span className="font-medium text-gray-900 dark:text-white capitalize">
            {node.node_type}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">OS:</span>
          <span className="font-medium text-gray-900 dark:text-white">
            {node.os_type || 'Unknown'}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600 dark:text-gray-400">Last seen:</span>
          <span className="font-medium text-gray-900 dark:text-white text-xs">
            {lastSeen}
          </span>
        </div>
      </div>

      {/* View Button */}
      <button
        onClick={onView}
        className="w-full py-2 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-900 dark:text-white rounded-lg transition font-medium"
      >
        View Details
      </button>
    </div>
  );
};

export default Nodes;
