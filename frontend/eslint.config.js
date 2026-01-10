import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    rules: {
      // Downgrade to warnings for gradual migration
      '@typescript-eslint/no-explicit-any': 'warn',
      '@typescript-eslint/no-unused-vars': ['warn', { argsIgnorePattern: '^_' }],
      'react-refresh/only-export-components': 'warn',
      // Allow setState in effects - common pattern for sync with props
      'react-hooks/set-state-in-effect': 'off',
      // Treat exhaustive-deps as warning
      'react-hooks/exhaustive-deps': 'warn',
      // Disable strict React compiler rules
      'react-hooks/rules-of-hooks': 'error', // Keep this one
      'react-hooks/static-components': 'off',
      'react-hooks/prefer-use-state-lazy-initialization': 'off',
      'react-hooks/preserve-manual-memoization': 'off',
      'react-hooks/purity': 'off',
      // Disable no-useless-escape for regex patterns
      'no-useless-escape': 'warn',
    },
  },
])
