import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { sentryVitePlugin } from '@sentry/vite-plugin'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [
      react(),
      tailwindcss(),
      // Sentry source maps plugin - only enabled when auth token is available
      env.SENTRY_AUTH_TOKEN &&
        sentryVitePlugin({
          org: env.SENTRY_ORG || 'grantradar',
          project: env.SENTRY_PROJECT || 'grantradar-frontend',
          authToken: env.SENTRY_AUTH_TOKEN,

          // Upload source maps to Sentry
          sourcemaps: {
            // Assets to upload (relative to build output)
            assets: './dist/**',
            // Don't delete source maps after upload (keep for debugging)
            filesToDeleteAfterUpload: [],
          },

          // Release configuration
          release: {
            name: `grantradar-frontend@${env.npm_package_version || '1.0.0'}`,
            // Automatically associate commits if in git repo
            setCommits: {
              auto: true,
              ignoreMissing: true,
            },
          },

          // Telemetry
          telemetry: false,

          // Disable in development
          disable: mode === 'development',

          // Debug mode
          debug: mode === 'development',
        }),
    ].filter(Boolean),

    build: {
      // Generate source maps for Sentry
      sourcemap: true,
    },
  }
})
