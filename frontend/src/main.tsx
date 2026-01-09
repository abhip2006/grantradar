import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import * as Sentry from '@sentry/react'
import './index.css'
import App from './App.tsx'

// Initialize Sentry error tracking
const SENTRY_DSN = import.meta.env.VITE_SENTRY_DSN

if (SENTRY_DSN) {
  Sentry.init({
    dsn: SENTRY_DSN,
    environment: import.meta.env.VITE_SENTRY_ENVIRONMENT || import.meta.env.MODE,
    release: `grantradar-frontend@${import.meta.env.VITE_APP_VERSION || '1.0.0'}`,

    // Performance monitoring
    integrations: [
      Sentry.browserTracingIntegration(),
      Sentry.replayIntegration({
        // Mask all text and block all media for privacy
        maskAllText: false,
        blockAllMedia: false,
      }),
    ],

    // Performance monitoring sample rates
    tracesSampleRate: import.meta.env.PROD ? 0.1 : 1.0, // 10% in prod, 100% in dev
    tracePropagationTargets: [
      'localhost',
      /^https:\/\/.*\.grantradar\.com/,
      /^https:\/\/.*\.railway\.app/,
    ],

    // Session replay sample rates
    replaysSessionSampleRate: import.meta.env.PROD ? 0.1 : 0, // 10% in prod, disabled in dev
    replaysOnErrorSampleRate: 1.0, // Always capture replays on errors

    // Filter out non-actionable errors
    beforeSend(event, hint) {
      const error = hint.originalException

      // Filter out network errors that are expected
      if (error instanceof Error) {
        const message = error.message.toLowerCase()
        if (
          message.includes('network request failed') ||
          message.includes('failed to fetch') ||
          message.includes('load failed')
        ) {
          // Check if this is from a health check or similar expected failure
          const breadcrumbs = event.breadcrumbs || []
          const isHealthCheck = breadcrumbs.some(
            (b) => b.data?.url?.includes('/health')
          )
          if (isHealthCheck) {
            return null
          }
        }
      }

      return event
    },

    // Debug mode in development
    debug: import.meta.env.DEV,
  })

  console.log('Sentry initialized for error tracking')
} else {
  console.log('Sentry DSN not configured, error tracking disabled')
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
