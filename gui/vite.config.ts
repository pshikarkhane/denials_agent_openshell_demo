import { defineConfig, type Plugin } from 'vitest/config';

/**
 * public/architecture.html is a static slide; Vite's HTML fallback would also answer
 * the app route /architecture with it (it tries "<path>.html"). Send the bare route to
 * the app shell first. Any other static host needs the same rule: /architecture is an
 * app route, /architecture.html is the slide.
 */
const architectureRoute = (): Plugin => {
  const rewrite = (req: { url?: string }, _res: unknown, next: () => void) => {
    if (req.url && req.url.split('?')[0] === '/architecture') req.url = '/index.html';
    next();
  };
  return {
    name: 'architecture-route',
    configureServer: (server) => void server.middlewares.use(rewrite),
    configurePreviewServer: (server) => void server.middlewares.use(rewrite),
  };
};

export default defineConfig({
  // No React plugin on purpose (fewer dependencies): JSX is compiled using tsconfig's "jsx": "react-jsx".
  plugins: [architectureRoute()],
  server: { port: 5173, strictPort: true },
  test: {
    environment: 'node',
    include: ['test/**/*.test.{ts,tsx,mjs}'],
    testTimeout: 20000,
  },
});
