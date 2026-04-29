import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      input: {
        background: path.resolve(__dirname, 'src/background.ts'),
        'content-script': path.resolve(__dirname, 'src/content-script.ts'),
        sidepanel: path.resolve(__dirname, 'sidepanel/index.html'),
        popup: path.resolve(__dirname, 'popup/index.html'),
      },
      output: {
        entryFileNames: (chunk) => {
          if (['background', 'content-script'].includes(chunk.name)) {
            return '[name].js'
          }
          return 'assets/[name]-[hash].js'
        },
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: (assetInfo) => {
          const info = assetInfo.name || ''
          if (info.endsWith('.css')) {
            return 'assets/[name]-[hash][extname]'
          }
          return 'assets/[name]-[hash][extname]'
        },
      },
    },
    outDir: 'dist',
    emptyOutDir: true,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
