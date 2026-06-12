# Architecture Decision Records

Use ADRs to record significant design decisions in this FastAPI AI server.

Write an ADR when:

- an AI agent made a design decision without prior user approval
- a route path, response schema, or AI pipeline behavior changed
- a new external API dependency was introduced
- multiple implementation options were plausible
- future agents need to know why the code is shaped this way

Do not write an ADR for small bug fixes, formatting, or obvious framework wiring.

## File Name

```text
NNNN-short-title.md
```

Example:

```text
0001-keep-step2-response-compatible-with-spring.md
```

## Template

```markdown
# <Decision Title>

Date:
Status: proposed | accepted | superseded

## Context

## Decision

## Alternatives Considered

## Consequences

## Follow-up Questions
```
