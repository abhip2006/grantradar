import { Outlet } from 'react-router-dom';
import { Navbar } from './Navbar';
import { ToastContainer } from './Toast';

export function Layout() {
  return (
    <div className="min-h-screen bg-[var(--gr-bg-primary)]">
      <Navbar />
      <main>
        <Outlet />
      </main>
      <ToastContainer />
    </div>
  );
}

export function AuthLayout() {
  return (
    <div className="min-h-screen bg-[var(--gr-bg-primary)]">
      <main>
        <Outlet />
      </main>
      <ToastContainer />
    </div>
  );
}

export default Layout;
