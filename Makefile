.PHONY: dev-backend dev-frontend test openapi synth eval

dev-backend:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

test:
	cd backend && uv run pytest -q

openapi:
	cd backend && uv run python scripts/export_openapi.py && cd ../frontend && npm run gen:api

synth:
	cd backend && uv run python scripts/generate_synthetic.py

eval:
	cd backend && uv run python scripts/eval_extraction.py
