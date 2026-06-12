# FastAPI AI Harness Playbooks

Use these playbooks for repeated work in the PICKD FastAPI AI server.

## Add A FastAPI Feature

1. Find the affected route in `app/api/router.py`.
2. Find or create the Pydantic schema in `app/schemas/`.
3. Check the shared contract in the PICKD monorepo: `contracts/openapi.yaml` and `docs/API_CONTRACT.md`.
4. Ask the user before choosing a new route path, response shape, breaking API change, or AI pipeline behavior.
5. Implement logic in `app/services/`.
6. Keep route functions thin: parse input, call service, return response, handle HTTP errors.
7. Add service tests for success, failure, and boundary branches.
8. Add a route smoke check when request or response behavior changes.
9. Check Spring `AiClient` compatibility if Spring calls the route.
10. Update `docs/ai-harness/user-flows.md` if the user-visible flow changes.
11. Update the shared OpenAPI contract if endpoint, request, response, status code, or error shape changes.

## Change A Spring-Called Route

1. Confirm the current route path and method.
2. Check Spring `AiClient.java` for the exact request.
3. Check the Java DTO in `global/infra/ai/dto`.
4. Check `contracts/openapi.yaml` and `docs/API_CONTRACT.md` for the shared API contract.
5. Keep field names and nullability compatible unless the user approved a breaking change.
6. Add or update a FastAPI service test.
7. Note the compatibility impact in the final summary.

## Debug FastAPI Failure

1. Check `GET /health`.
2. Check whether the request reaches `app/api/router.py`.
3. Separate validation errors, service exceptions, external API key failures, and timeouts.
4. Check `.env` presence without printing secret values.
5. Mock external API clients for deterministic unit tests.
6. Use `test_api.sh` only when real external API calls are acceptable.

## Promote Repeated Requests To A Skill

1. Record repeated request patterns in `docs/ai-harness/skill-candidates.local.md`.
2. When the pattern is stable, move the reusable procedure to this playbook.
3. If it becomes broadly reusable and deterministic, create a dedicated skill later.
4. Never include private prompt text or secret values in versioned files.
