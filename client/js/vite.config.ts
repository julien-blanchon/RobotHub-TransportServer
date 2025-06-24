import { defineConfig } from 'vite';
import { resolve } from 'path';
import dts from 'vite-plugin-dts';

export default defineConfig({
  plugins: [
    dts({
      insertTypesEntry: true,
      rollupTypes: true,
    }),
  ],
  build: {
    lib: {
      entry: {
        index: resolve('src/index.ts'),
        video: resolve('src/video/index.ts'),
        robotics: resolve('src/robotics/index.ts'),
      },
      formats: ['es'],
    },
    rollupOptions: {
      external: ['eventemitter3'],
      output: {
        preserveModules: false,
        exports: 'named',
      },
    },
    target: 'esnext',
    minify: false,
  },
  resolve: {
    alias: {
      '@': resolve('src'),
      '@/video': resolve('src/video'),
      '@/robotics': resolve('src/robotics'),
    },
  },
}); 