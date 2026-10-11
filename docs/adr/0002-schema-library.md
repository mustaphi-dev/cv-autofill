# 0002. Schema library: Zod 4

Date: 2026-10-11. Status: accepted.

## Context

Every message, stored object and API payload is validated at runtime, and TypeScript types are inferred from the schemas (spec section 5). The backend's Pydantic models are generated from JSON Schema exported from these schemas, so the two sides cannot drift.

## Decision

Use Zod 4 (4.6.5 at the time of writing). It infers types and exports JSON Schema with the built-in `z.toJSONSchema()`, so no extra converter is needed.

Alternatives considered:

- TypeBox. Its schemas are JSON Schema already, but its fast validator compiles code with `new Function`, which extension Content Security Policy blocks.
- Valibot. Smaller bundles, but needs a separate JSON Schema converter. Bundle size barely matters in an extension.

## Consequences

- Rules that JSON Schema cannot express (custom refinements, such as "end date after start date") exist only on the TypeScript side. Keep them few, and test the backend's equivalents against the same cases.
- To verify in M2: Zod 4 can speed up validation with generated code. It should fall back on its own where the security policy forbids that, and `z.config({ jitless: true })` forces the fallback. Confirm extension pages show no CSP errors.
