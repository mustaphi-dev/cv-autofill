import { expect, test } from "vitest";
import { Profile, RULES } from "../src/index";
import cases from "../fixtures/cases.json";

// The backend runs the same cases against its Python models
// (backend/tests/test_profile.py), so the two sides cannot drift apart.

test.each(cases)("$name", ({ valid, rule, profile }) => {
  const result = Profile.safeParse(profile);
  expect(result.success).toBe(valid);
  if (rule) expect(result.error?.issues.map((i) => i.message)).toContain(rule);
});

test("every rule in the schema has a shared case", () => {
  const covered = cases.map((c) => ("rule" in c ? c.rule : undefined));
  for (const rule of Object.values(RULES)) expect(covered).toContain(rule);
});
