import * as z from "zod";

// Zod can speed up validation by generating code with `new Function`, which
// extension pages forbid (their CSP has no unsafe-eval). Probing for it logs a
// CSP error, so turn it off everywhere. Profiles are small; speed is not lost.
z.config({ jitless: true });

// The profile (spec section 5). Every section is its own strict type, so an
// entry from one section can never validate as another (unknown keys are
// rejected). A list's array position is its order. Fields are optional so a
// half-finished profile is still valid; missing data is reported at fill time.

const NAME = 300;
const URL_MAX = 2048;
const BULLET = 1000;
const SUMMARY = 5000;
const MAX_ENTRIES = 100;
const MAX_BULLETS = 50;
const MAX_TAGS = 50;

// Rules are written as regexes so the exported JSON Schema (used by the
// backend) carries them too: text is not blank, links are http(s) only.
const text = (max = NAME) => z.string().trim().max(max).regex(/\S/);
const url = z
  .url()
  .max(URL_MAX)
  .regex(/^https?:\/\//i);
const tags = z.array(text()).max(MAX_TAGS);
const bullets = z.array(text(BULLET)).max(MAX_BULLETS);
const id = z.uuid();

export const YearMonth = z.strictObject({
  year: z.int().min(1900).max(2100),
  month: z.int().min(1).max(12).optional(),
});
export type YearMonth = z.infer<typeof YearMonth>;

const description = {
  bullets: bullets.optional(),
  variants: z
    .strictObject({ short: bullets.optional(), long: bullets.optional() })
    .optional(),
};

// Compares by month when both dates have one, otherwise by year.
function notBefore(later: YearMonth, earlier: YearMonth): boolean {
  if (later.year !== earlier.year) return later.year > earlier.year;
  return (later.month ?? 12) >= (earlier.month ?? 1);
}

const span = {
  start: YearMonth.optional(),
  end: YearMonth.optional(),
  current: z.boolean().optional(),
};

type Span = {
  start?: YearMonth | undefined;
  end?: YearMonth | undefined;
  current?: boolean | undefined;
};

// Applied to every entry type that has a date span.
function withSpan<T extends z.ZodType<Span>>(schema: T): T {
  return schema
    .refine((e) => !(e.current === true && e.end), {
      error: "A current entry cannot have an end date",
      path: ["end"],
    })
    .refine((e) => !e.start || !e.end || notBefore(e.end, e.start), {
      error: "End date is before start date",
      path: ["end"],
    });
}

export const Personal = z.strictObject({
  firstName: text().optional(),
  lastName: text().optional(),
  preferredName: text().optional(),
  headline: text().optional(),
  email: z.email().max(NAME).optional(),
  phone: z
    .strictObject({
      countryCode: z.string().regex(/^\+\d{1,4}$/),
      number: z.string().regex(/^\d{4,15}$/),
    })
    .optional(),
  address: z
    .strictObject({
      street: text().optional(),
      city: text().optional(),
      region: text().optional(),
      postcode: text(20).optional(),
      country: text().optional(),
    })
    .optional(),
});

export const Link = z
  .strictObject({
    id,
    kind: z.enum([
      "linkedin",
      "github",
      "portfolio",
      "website",
      "scholar",
      "orcid",
      "other",
    ]),
    label: text().optional(),
    url,
  })
  .refine((l) => l.kind !== "other" || l.label, {
    error: "A link of kind 'other' needs a label",
    path: ["label"],
  });

export const Work = withSpan(
  z.strictObject({
    id,
    company: text().optional(),
    title: text().optional(),
    employmentType: z
      .enum(["full-time", "part-time", "contract", "internship", "freelance"])
      .optional(),
    location: text().optional(),
    workplace: z.enum(["remote", "hybrid", "on-site"]).optional(),
    ...span,
    ...description,
    aliases: tags.optional(),
  }),
);

export const Project = withSpan(
  z.strictObject({
    id,
    name: text().optional(),
    role: text().optional(),
    organisation: text().optional(),
    ...span,
    url: url.optional(),
    repositoryUrl: url.optional(),
    technologies: tags.optional(),
    ...description,
  }),
);

export const Education = withSpan(
  z.strictObject({
    id,
    school: text().optional(),
    degree: text().optional(),
    fieldOfStudy: text().optional(),
    minor: text().optional(),
    ...span,
    grade: text().optional(),
    thesisTitle: text().optional(),
    modules: tags.optional(),
    ...description,
    aliases: tags.optional(),
  }),
);

export const Publication = z.strictObject({
  id,
  title: text().optional(),
  authors: tags.optional(),
  venue: text().optional(),
  date: YearMonth.optional(),
  doi: text().optional(),
  url: url.optional(),
  status: z
    .enum(["published", "accepted", "under-review", "preprint"])
    .optional(),
});

export const Certification = z
  .strictObject({
    id,
    name: text().optional(),
    issuer: text().optional(),
    issueDate: YearMonth.optional(),
    expiryDate: YearMonth.optional(),
    credentialId: text().optional(),
    url: url.optional(),
  })
  .refine(
    (c) =>
      !c.issueDate || !c.expiryDate || notBefore(c.expiryDate, c.issueDate),
    { error: "Expiry date is before issue date", path: ["expiryDate"] },
  );

export const Skill = z.strictObject({
  id,
  name: text().optional(),
  category: text().optional(),
  level: text().optional(),
  years: z.number().min(0).max(60).optional(),
});

export const Language = z.strictObject({
  id,
  language: text().optional(),
  proficiency: z
    .enum(["native", "fluent", "professional", "conversational", "basic"])
    .optional(),
});

export const Award = z.strictObject({
  id,
  title: text().optional(),
  issuer: text().optional(),
  date: YearMonth.optional(),
  ...description,
});

export const Volunteering = withSpan(
  z.strictObject({
    id,
    organisation: text().optional(),
    role: text().optional(),
    ...span,
    ...description,
    aliases: tags.optional(),
  }),
);

export const Course = z.strictObject({
  id,
  name: text().optional(),
  provider: text().optional(),
  completionDate: YearMonth.optional(),
});

export const Membership = z.strictObject({
  id,
  organisation: text().optional(),
  level: text().optional(),
  start: YearMonth.optional(),
});

export const Talk = z.strictObject({
  id,
  title: text().optional(),
  event: text().optional(),
  date: YearMonth.optional(),
  url: url.optional(),
});

export const Patent = z.strictObject({
  id,
  title: text().optional(),
  number: text().optional(),
  status: text().optional(),
  date: YearMonth.optional(),
});

export const Reference = z.strictObject({
  id,
  name: text().optional(),
  title: text().optional(),
  organisation: text().optional(),
  email: z.email().max(NAME).optional(),
  phone: text(30).optional(),
  relationship: text().optional(),
});

const list = <T extends z.ZodType>(entry: T) =>
  z.array(entry).max(MAX_ENTRIES).default([]);

export const Profile = z
  .strictObject({
    schemaVersion: z.literal(1),
    personal: Personal.optional(),
    summary: text(SUMMARY).optional(),
    links: list(Link),
    work: list(Work),
    projects: list(Project),
    education: list(Education),
    publications: list(Publication),
    certifications: list(Certification),
    skills: list(Skill),
    languages: list(Language),
    awards: list(Award),
    volunteering: list(Volunteering),
    courses: list(Course),
    memberships: list(Membership),
    talks: list(Talk),
    patents: list(Patent),
    references: list(Reference),
  })
  .refine(
    (p) => {
      const ids = Object.values(p).flatMap((v) =>
        Array.isArray(v) ? v.map((e) => e.id) : [],
      );
      return new Set(ids).size === ids.length;
    },
    { error: "Two entries share the same id" },
  );
export type Profile = z.infer<typeof Profile>;

// Messages from extension pages to the background (spec section 5). The
// background validates every message and only accepts them from extension
// pages, never from content scripts on job sites.
export const Request = z.discriminatedUnion("type", [
  z.strictObject({ type: z.literal("profile.get") }),
  z.strictObject({ type: z.literal("profile.save"), profile: Profile }),
  z.strictObject({ type: z.literal("data.deleteAll") }),
]);
export type Request = z.infer<typeof Request>;

export const Reply = z.union([
  z.strictObject({ ok: z.literal(true), data: z.unknown() }),
  z.strictObject({
    ok: z.literal(false),
    error: z.enum([
      "forbidden",
      "invalid_request",
      "stored_profile_invalid",
      "storage_failed",
    ]),
  }),
]);
export type Reply = z.infer<typeof Reply>;

export type Issue = z.core.$ZodIssue;
