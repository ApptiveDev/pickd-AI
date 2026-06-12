# PICKD FastAPI AI Server Agent Guide

This file is the source of truth for AI coding agents working in the PICKD FastAPI AI server.
Follow it before editing code.

## Server Context

- This directory is the PICKD AI worker server.
- Framework: FastAPI.
- App entry point: `app/main.py`.
- API router: `app/api/router.py`.
- Local port: `8000`.
- Health check: `GET /health`.
- The Spring server normally calls this server through `ai-server.url=http://localhost:8000`.
- Never copy real API keys or `.env` values into code, docs, tests, or commit messages.

## Key Code Areas

- `app/main.py`: creates the FastAPI app and includes the API router.
- `app/api/router.py`: HTTP route layer. Keep it thin.
- `app/schemas/`: Pydantic request and response DTOs.
- `app/services/`: AI, parsing, merge, extraction, and analysis logic.
- `app/core/config.py`: environment variable names and external API endpoint constants.
- `tests/`: unit tests for service behavior.
- `test_api.sh`: manual API smoke checks that may call external APIs.

## First Step For Every Feature Request

Before implementing, identify and report the likely change scope:

- FastAPI route or endpoint affected
- Pydantic schema affected
- service function affected
- Spring `AiClient` route or DTO compatibility impact
- whether `contracts/openapi.yaml` or `docs/API_CONTRACT.md` in the PICKD monorepo must change
- external API dependency and key requirements
- required unit tests and smoke checks
- any design decision that needs user confirmation

If the request implies a new route, new response shape, new AI pipeline behavior, or new user flow that was not explicitly requested, ask the user before deciding.

## FastAPI Implementation Order

Use this order for feature work unless the request is clearly only a small bug fix:

1. Confirm or create the Pydantic request and response schema.
2. Confirm any data model or DTO mapping needed by Spring.
3. Implement business and AI logic in `app/services/`.
4. Define validation and failure cases.
5. Add HTTP error handling in the route layer.
6. Keep `app/api/router.py` thin and delegate to services.
7. Add service tests for branches and conditions.
8. Add API smoke checks when route behavior changes.
9. Verify Spring `AiClient` and Java DTO compatibility.
10. Update `docs/ai-harness/user-flows.md` if the user-visible flow changes.

## API Contract Rules

The shared API contract source of truth lives in the PICKD monorepo:

- `contracts/openapi.yaml`
- `docs/API_CONTRACT.md`

Before adding or changing any public FastAPI API, especially routes called by Spring:

- check whether the endpoint, method, request, response, status code, or error shape changes
- update the shared OpenAPI contract when the public API changes
- update `docs/ai-harness/user-flows.md` when the user-visible flow changes
- ask the user before making a breaking change

Breaking changes include endpoint path changes, method changes, new required request fields, deleted or retyped response fields, changed status code meaning, and changed error response shape.

## Spring Compatibility Rules

Spring currently depends on these FastAPI routes:

- `POST /api/v1/extract-experiences/step1`
- `POST /api/v1/extract-experiences/step2`
- `POST /api/v1/experiences/merge-check`
- `POST /api/v1/analyze/url`
- `POST /api/v1/analyze/pdf`

When changing any of these:

- keep route paths stable unless the user approved a breaking change
- keep response field names compatible with Spring DTOs
- preserve nullable fields unless the user approved stricter validation
- document any behavior change in `docs/ai-harness/user-flows.md`
- update Spring DTOs and tests if compatibility changes are required

## External API Rules

Environment variable names are defined in `app/core/config.py`.

Known keys:

- `OPENAI_API_KEY`
- `UPSTAGE_API_KEY`
- `GOOGLE_API_KEY`
- `FIRECRAWL_API_KEY`

For tests, prefer mocked clients when possible. Only run real external API calls when the user expects it and required keys are available.

## Documentation Rules

- Update `docs/ai-harness/user-flows.md` whenever a feature flow changes.
- Update `docs/ai-harness/playbooks.md` only for reusable team/project procedures.
- If an AI agent makes a significant design decision without prior user approval, write an ADR in `docs/adr/`.
- Personal prompt logs and skill candidates must stay local-only as `docs/ai-harness/*.local.md`.

## After Coding: Show Code In Layer Order

After writing code, present the changed code to the user in low-to-high layer order.

For FastAPI, use this order:

1. Pydantic schemas and DTO-style models
2. data models, persistence helpers, or external API adapters if present
3. services, pipeline branches, validation, and exceptions
4. routers and HTTP endpoints
5. tests and verification results

When the change must also be understood by Spring, include the matching Spring DTO or `AiClient` compatibility note after the FastAPI layers. Do not lead with the router unless the change only touched routing.

## Verification

Prefer focused verification:

- service unit tests for parsing, AI response shaping, merge logic, and validation branches
- `/health` smoke check for app startup
- route smoke checks for changed endpoints

Some smoke checks call paid or rate-limited external APIs. State clearly when they were skipped.
