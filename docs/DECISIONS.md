# Decisions

- B1: Routers are registered through a `ROUTERS` list in `app/main.py`; it starts empty and later steps append to it.
- B1: The SPA fallback is a catch-all GET route registered after `/api` and `/samples`; it returns 404 for `/api/*` and `/samples/*`.
- F1: Frontend pins TypeScript ~5.9 (Vite template default is 6.x) because openapi-typescript 7 requires a TypeScript 5 peer.
