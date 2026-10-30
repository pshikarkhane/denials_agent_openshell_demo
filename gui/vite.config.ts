import { defineConfig } from 'vitest/config';

export default defineConfig({
  // No React plugin on purpose (fewer dependencies): JSX is compiled using tsconfig's "jsx": "react-jsx".
  server: { port: 5173, strictPort: true },
  test: {
    environment: 'node',
    include: ['test/**/*.test.{ts,tsx,mjs}'],
    testTimeout: 20000,
  },
});
