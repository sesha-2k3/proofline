# Decisions

- B1: Routers are registered through a `ROUTERS` list in `app/main.py`; it starts empty and later steps append to it.
- B1: The SPA fallback is a catch-all GET route registered after `/api` and `/samples`; it returns 404 for `/api/*` and `/samples/*`.
