import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { AuthProvider } from './contexts/AuthContext';
import { ToastProvider } from './contexts/ToastContext';
import { Layout, AuthLayout } from './components/Layout';
import { ProtectedRoute } from './components/ProtectedRoute';

// Pages
import { Landing } from './pages/Landing';
import { Auth } from './pages/Auth';
import { Dashboard } from './pages/Dashboard';
import { GrantDetail } from './pages/GrantDetail';
import { Compare } from './pages/Compare';
import { Pipeline } from './pages/Pipeline';
import { Settings } from './pages/Settings';
import { PrivacyPolicy } from './pages/PrivacyPolicy';
import { Terms } from './pages/Terms';
import { Contact } from './pages/Contact';
import { About } from './pages/About';
import { FAQ } from './pages/FAQ';
import { Pricing } from './pages/Pricing';
import { FunderInsights } from './pages/FunderInsights';
import { FunderDetail } from './pages/FunderDetail';
import { Calendar } from './pages/Calendar';
import { Analytics } from './pages/Analytics';
import { Forecast } from './pages/Forecast';
import { Deadlines } from './pages/Deadlines';
import { Integrations } from './pages/Integrations';
import { Templates } from './pages/Templates';
import { AITools } from './pages/AITools';
import { Kanban } from './pages/Kanban';

// Create React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              {/* Public routes */}
              <Route element={<Layout />}>
                <Route path="/" element={<Landing />} />
                <Route path="/privacy" element={<PrivacyPolicy />} />
                <Route path="/terms" element={<Terms />} />
                <Route path="/contact" element={<Contact />} />
                <Route path="/about" element={<About />} />
                <Route path="/faq" element={<FAQ />} />
                <Route path="/pricing" element={<Pricing />} />
              </Route>

              {/* Auth routes (no navbar) */}
              <Route element={<AuthLayout />}>
                <Route path="/auth" element={<Auth />} />
              </Route>

              {/* Protected routes */}
              <Route element={<Layout />}>
                <Route
                  path="/dashboard"
                  element={
                    <ProtectedRoute>
                      <Dashboard />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/grants/:id"
                  element={
                    <ProtectedRoute>
                      <GrantDetail />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/settings"
                  element={
                    <ProtectedRoute>
                      <Settings />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/compare"
                  element={
                    <ProtectedRoute>
                      <Compare />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/pipeline"
                  element={
                    <ProtectedRoute>
                      <Pipeline />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/kanban"
                  element={
                    <ProtectedRoute>
                      <Kanban />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/funders"
                  element={
                    <ProtectedRoute>
                      <FunderInsights />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/funders/:funderName"
                  element={
                    <ProtectedRoute>
                      <FunderDetail />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/calendar"
                  element={
                    <ProtectedRoute>
                      <Calendar />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/deadlines"
                  element={
                    <ProtectedRoute>
                      <Deadlines />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/analytics"
                  element={
                    <ProtectedRoute>
                      <Analytics />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/forecast"
                  element={
                    <ProtectedRoute>
                      <Forecast />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/integrations"
                  element={
                    <ProtectedRoute>
                      <Integrations />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/templates"
                  element={
                    <ProtectedRoute>
                      <Templates />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/ai-tools"
                  element={
                    <ProtectedRoute>
                      <AITools />
                    </ProtectedRoute>
                  }
                />
              </Route>

              {/* 404 fallback */}
              <Route
                path="*"
                element={
                  <div className="min-h-screen flex items-center justify-center bg-[var(--gr-bg-primary)]">
                    <div className="text-center">
                      <h1 className="text-6xl font-display font-bold text-[var(--gr-amber-400)] mb-4">404</h1>
                      <p className="text-[var(--gr-text-secondary)] mb-6">Page not found</p>
                      <a href="/" className="btn-primary">
                        Go Home
                      </a>
                    </div>
                  </div>
                }
              />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </ToastProvider>
    </QueryClientProvider>
  );
}

export default App;
