# Resume Taylor frontend

Vite + React + TypeScript + Tailwind, with Radix primitives. It talks to the Python
backend over a token-protected REST API and Server-Sent Events.

```text
src/
  features/     one folder per screen (workspace, projects, evidence, ...); page-only pieces
                live in the feature's components/ or editor/ folder
  components/   ui/ (primitives), layout/ (app shell), shared/ (used across features)
  lib/api/      client.ts (fetch + token), queries.ts (react-query hooks), sse.ts,
                types.ts, schema.d.ts (generated from the server: npm run gen:api)
  lib/          theme, utils, hooks
```

```bash
npm install
npm run dev        # hot reload; pair with: python launcher.py --dev
npm run check      # typecheck + lint + tests (tests sit next to the code as *.test.ts[x])
npm run build      # writes dist/, which is committed so users don't need Node.js
```

After changing a Pydantic request model on the server, run `npm run gen:api`.
