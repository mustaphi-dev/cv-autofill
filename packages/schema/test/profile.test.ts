import { describe, expect, test } from "vitest";
import { Profile, Project, Publication, Work } from "../src/index";

// Frozen example profiles, one per released schema version. Never edit one:
// add a new file for each new version. If an old one stops loading, write a
// migration for it (spec section 5).
import v1 from "../fixtures/profile.v1.json";

const uuid = () => crypto.randomUUID();

const issues = (r: { success: boolean; error?: { issues: unknown[] } }) =>
  r.success ? [] : (r.error?.issues ?? []);

describe("Profile", () => {
  test.each([["v1", v1]])("frozen %s profile still loads", (_, raw) => {
    expect(issues(Profile.safeParse(raw))).toEqual([]);
  });

  test("accepts a minimal profile and fills empty sections", () => {
    const p = Profile.parse({ schemaVersion: 1 });
    expect(p.work).toEqual([]);
    expect(p.references).toEqual([]);
  });

  test("rejects other schema versions", () => {
    expect(Profile.safeParse({ schemaVersion: 2 }).success).toBe(false);
  });

  test("rejects unknown keys instead of dropping them", () => {
    expect(Profile.safeParse({ ...v1, extra: 1 }).success).toBe(false);
  });

  test("rejects two entries with the same id", () => {
    const id = uuid();
    const p = {
      schemaVersion: 1,
      work: [{ id }],
      projects: [{ id }],
    };
    expect(Profile.safeParse(p).success).toBe(false);
  });

  test("rejects too many entries in a section", () => {
    const work = Array.from({ length: 101 }, () => ({ id: uuid() }));
    expect(Profile.safeParse({ schemaVersion: 1, work }).success).toBe(false);
  });
});

describe("sections never mix", () => {
  test("a project cannot validate as a work entry", () => {
    expect(Work.safeParse(v1.projects[0]).success).toBe(false);
  });

  test("a publication cannot validate as a project", () => {
    expect(Project.safeParse(v1.publications[0]).success).toBe(false);
  });

  test("a work entry cannot validate as a publication", () => {
    expect(Publication.safeParse(v1.work[0]).success).toBe(false);
  });
});

describe("dates", () => {
  const work = (e: object) => Work.safeParse({ id: uuid(), ...e }).success;

  test("rejects an end date on a current entry", () => {
    expect(work({ current: true, end: { year: 2024 } })).toBe(false);
  });

  test("rejects an end before the start", () => {
    expect(
      work({ start: { year: 2024, month: 5 }, end: { year: 2024, month: 4 } }),
    ).toBe(false);
    expect(work({ start: { year: 2024 }, end: { year: 2023 } })).toBe(false);
  });

  test("accepts same-year dates when a month is missing", () => {
    expect(work({ start: { year: 2024, month: 9 }, end: { year: 2024 } })).toBe(
      true,
    );
    expect(work({ start: { year: 2024 }, end: { year: 2024, month: 1 } })).toBe(
      true,
    );
  });

  test("rejects impossible months", () => {
    expect(work({ start: { year: 2024, month: 13 } })).toBe(false);
  });
});

describe("field rules", () => {
  test("rejects non-http links", () => {
    const link = { id: uuid(), kind: "website", url: "javascript:alert(1)" };
    expect(Profile.safeParse({ schemaVersion: 1, links: [link] }).success).toBe(
      false,
    );
  });

  test("requires a label on links of kind 'other'", () => {
    const link = { id: uuid(), kind: "other", url: "https://example.com" };
    expect(Profile.safeParse({ schemaVersion: 1, links: [link] }).success).toBe(
      false,
    );
  });

  test("rejects blank and over-long text", () => {
    expect(Work.safeParse({ id: uuid(), company: "   " }).success).toBe(false);
    expect(
      Work.safeParse({ id: uuid(), company: "x".repeat(301) }).success,
    ).toBe(false);
  });

  test("trims text", () => {
    expect(Work.parse({ id: uuid(), company: "  Acme  " }).company).toBe(
      "Acme",
    );
  });

  test("requires the phone country code to start with +", () => {
    const personal = { phone: { countryCode: "44", number: "7700900123" } };
    expect(Profile.safeParse({ schemaVersion: 1, personal }).success).toBe(
      false,
    );
  });
});
