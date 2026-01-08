// DEV NOTE: Imports commented out during dev bypass - restore when enabling auth
// import { Navigate, useLocation } from 'react-router-dom';
// import { useAuth } from '../contexts/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  // DEV BYPASS: Always allow access
  // TODO: Restore auth check when ready:
  // const { isAuthenticated } = useAuth();
  // const location = useLocation();
  // if (!isAuthenticated) {
  //   return <Navigate to="/auth" state={{ from: location }} replace />;
  // }
  return <>{children}</>;
}

export default ProtectedRoute;
