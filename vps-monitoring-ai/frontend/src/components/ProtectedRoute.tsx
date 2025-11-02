/**
 * Protected Route Component
 * Handles authentication and RBAC
 */
import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../store/authStore';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredPermission?: keyof ReturnType<typeof useAuthStore>['permissions'];
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredPermission,
}) => {
  const { isAuthenticated, permissions, checkTokenValidity } = useAuthStore();

  // Check token validity
  const isTokenValid = checkTokenValidity();

  if (!isAuthenticated || !isTokenValid) {
    return <Navigate to="/login" replace />;
  }

  // Check specific permission if required
  if (requiredPermission && !permissions[requiredPermission]) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <div className="text-6xl mb-4">🔒</div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            Access Denied
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            You don't have permission to access this page.
          </p>
        </div>
      </div>
    );
  }

  return <>{children}</>;
};

export default ProtectedRoute;
