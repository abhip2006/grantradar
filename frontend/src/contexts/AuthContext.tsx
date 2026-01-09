import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from 'react';
import { authApi } from '../services/api';
import { socketService } from '../services/socket';
import type { User, LoginCredentials, SignupData } from '../types';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  signup: (data: SignupData) => Promise<void>;
  logout: () => void;
  updateUser: (user: User) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// DEV BYPASS: Set to true to skip authentication (DEVELOPMENT ONLY)
// SECURITY: This must be false in production builds
const DEV_BYPASS_AUTH = import.meta.env.VITE_DEV_BYPASS_AUTH === 'true';
const MOCK_USER: User = {
  id: 'dev-user-123',
  email: 'dev@grantradar.com',
  name: 'Dev User',
  organization_name: 'GrantRadar Dev',
  organization_type: 'university',
  focus_areas: ['biomedical', 'technology'],
  created_at: new Date().toISOString(),
  has_profile: true,
};

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(DEV_BYPASS_AUTH ? MOCK_USER : null);
  const [isLoading, setIsLoading] = useState(!DEV_BYPASS_AUTH);

  // Initialize auth state from localStorage
  useEffect(() => {
    if (DEV_BYPASS_AUTH) {
      setIsLoading(false);
      return;
    }

    const initAuth = async () => {
      const token = localStorage.getItem('access_token');
      const storedUser = localStorage.getItem('user');

      if (token) {
        try {
          // Verify token is still valid by fetching current user
          const currentUser = await authApi.getCurrentUser();
          setUser(currentUser);
          localStorage.setItem('user', JSON.stringify(currentUser));
          socketService.connect(token);
        } catch {
          // Token is invalid, clear storage
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          localStorage.removeItem('user');
        }
      } else if (storedUser) {
        // No token but have user - clear invalid state
        localStorage.removeItem('user');
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = useCallback(async (credentials: LoginCredentials) => {
    // Get tokens from login endpoint
    const response = await authApi.login(credentials);

    // Store tokens
    localStorage.setItem('access_token', response.access_token);
    localStorage.setItem('refresh_token', response.refresh_token);

    // Fetch user data (backend doesn't return user with token)
    const currentUser = await authApi.getCurrentUser();
    localStorage.setItem('user', JSON.stringify(currentUser));
    setUser(currentUser);

    // Connect to websocket
    socketService.connect(response.access_token);
  }, []);

  const signup = useCallback(async (data: SignupData) => {
    // Get tokens from register endpoint
    const response = await authApi.signup(data);

    // Store tokens
    localStorage.setItem('access_token', response.access_token);
    localStorage.setItem('refresh_token', response.refresh_token);

    // Fetch user data (backend doesn't return user with token)
    const currentUser = await authApi.getCurrentUser();

    // Augment with signup data that backend might not store yet
    const augmentedUser: User = {
      ...currentUser,
      organization_name: data.organization_name || currentUser.name || '',
      organization_type: data.organization_type,
      focus_areas: data.focus_areas || [],
    };

    localStorage.setItem('user', JSON.stringify(augmentedUser));
    setUser(augmentedUser);

    // Connect to websocket
    socketService.connect(response.access_token);
  }, []);

  const logout = useCallback(() => {
    authApi.logout();
    socketService.disconnect();
    setUser(null);
  }, []);

  const updateUser = useCallback((updatedUser: User) => {
    setUser(updatedUser);
    localStorage.setItem('user', JSON.stringify(updatedUser));
  }, []);

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    signup,
    logout,
    updateUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

// Removed default export for better HMR compatibility
