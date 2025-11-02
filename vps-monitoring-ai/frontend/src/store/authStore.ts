/**
 * Authentication Store (Zustand)
 * Manages user authentication state and RBAC permissions
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { jwtDecode } from 'jwt-decode';
import { User, UserRole, Permissions, getRolePermissions } from '../types';

interface AuthState {
  user: User | null;
  token: string | null;
  permissions: Permissions;
  isAuthenticated: boolean;
  
  // Actions
  login: (token: string, user: User) => void;
  logout: () => void;
  updateUser: (user: User) => void;
  checkTokenValidity: () => boolean;
}

const defaultPermissions = getRolePermissions(UserRole.VIEWER);

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      permissions: defaultPermissions,
      isAuthenticated: false,

      login: (token: string, user: User) => {
        const permissions = getRolePermissions(user.role);
        set({
          token,
          user,
          permissions,
          isAuthenticated: true,
        });
      },

      logout: () => {
        set({
          user: null,
          token: null,
          permissions: defaultPermissions,
          isAuthenticated: false,
        });
      },

      updateUser: (user: User) => {
        const permissions = getRolePermissions(user.role);
        set({ user, permissions });
      },

      checkTokenValidity: () => {
        const { token } = get();
        if (!token) return false;

        try {
          const decoded: any = jwtDecode(token);
          const currentTime = Date.now() / 1000;
          
          if (decoded.exp < currentTime) {
            // Token expired
            get().logout();
            return false;
          }
          return true;
        } catch (error) {
          get().logout();
          return false;
        }
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        token: state.token,
        user: state.user,
      }),
    }
  )
);
