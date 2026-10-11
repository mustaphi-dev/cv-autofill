// What the editor shows for each profile field. A test checks this table
// against the exported JSON Schema, so a new schema field cannot be forgotten.

export type Field = {
  path: readonly string[];
  label: string;
  kind:
    | "text"
    | "email"
    | "url"
    | "long"
    | "lines"
    | "choice"
    | "check"
    | "number"
    | "date";
  options?: readonly string[];
};

const text = (path: string, label: string): Field => ({
  path: [path],
  label,
  kind: "text",
});
const lines = (path: string, label: string): Field => ({
  path: [path],
  label: `${label} (one per line)`,
  kind: "lines",
});
const date = (path: string, label: string): Field => ({
  path: [path],
  label,
  kind: "date",
});
const url = (path: string, label: string): Field => ({
  path: [path],
  label,
  kind: "url",
});
const choice = (path: string, label: string, options: string[]): Field => ({
  path: [path],
  label,
  kind: "choice",
  options,
});

const span = [
  date("start", "Start"),
  date("end", "End"),
  { path: ["current"], label: "Current", kind: "check" },
] satisfies Field[];

const description = [
  lines("bullets", "Description bullets"),
  {
    path: ["variants", "short"],
    label: "Short version bullets (one per line)",
    kind: "lines",
  },
  {
    path: ["variants", "long"],
    label: "Long version bullets (one per line)",
    kind: "lines",
  },
] satisfies Field[];

const aliases = lines("aliases", "Other names");

export const PERSONAL: Field[] = [
  text("firstName", "First name"),
  text("lastName", "Last name"),
  text("preferredName", "Preferred name"),
  text("headline", "Headline or current title"),
  { path: ["email"], label: "Email", kind: "email" },
  {
    path: ["phone", "countryCode"],
    label: "Phone country code (e.g. +44)",
    kind: "text",
  },
  {
    path: ["phone", "number"],
    label: "Phone number (digits only)",
    kind: "text",
  },
  { path: ["address", "street"], label: "Street", kind: "text" },
  { path: ["address", "city"], label: "City", kind: "text" },
  { path: ["address", "region"], label: "Region", kind: "text" },
  { path: ["address", "postcode"], label: "Postcode", kind: "text" },
  { path: ["address", "country"], label: "Country", kind: "text" },
];

export type ListSection = {
  key: string;
  label: string;
  singular: string;
  fields: Field[];
};

export const LISTS: ListSection[] = [
  {
    key: "links",
    label: "Links",
    singular: "Link",
    fields: [
      choice("kind", "Type", [
        "linkedin",
        "github",
        "portfolio",
        "website",
        "scholar",
        "orcid",
        "other",
      ]),
      text("label", "Label (needed for type 'other')"),
      url("url", "URL"),
    ],
  },
  {
    key: "work",
    label: "Work experience",
    singular: "Job",
    fields: [
      text("company", "Company"),
      text("title", "Job title"),
      choice("employmentType", "Employment type", [
        "full-time",
        "part-time",
        "contract",
        "internship",
        "freelance",
      ]),
      text("location", "Location"),
      choice("workplace", "Workplace", ["remote", "hybrid", "on-site"]),
      ...span,
      ...description,
      aliases,
    ],
  },
  {
    key: "projects",
    label: "Projects",
    singular: "Project",
    fields: [
      text("name", "Name"),
      text("role", "Role"),
      text("organisation", "Organisation or context"),
      ...span,
      url("url", "URL"),
      url("repositoryUrl", "Repository URL"),
      lines("technologies", "Technologies"),
      ...description,
    ],
  },
  {
    key: "education",
    label: "Education",
    singular: "Education entry",
    fields: [
      text("school", "School"),
      text("degree", "Degree"),
      text("fieldOfStudy", "Field of study"),
      text("minor", "Minor"),
      ...span,
      text("grade", "Grade or classification"),
      text("thesisTitle", "Thesis or dissertation title"),
      lines("modules", "Relevant modules"),
      ...description,
      aliases,
    ],
  },
  {
    key: "publications",
    label: "Publications",
    singular: "Publication",
    fields: [
      text("title", "Title"),
      lines("authors", "Authors, in order"),
      text("venue", "Journal or conference"),
      date("date", "Publication date"),
      text("doi", "DOI"),
      url("url", "URL"),
      choice("status", "Status", [
        "published",
        "accepted",
        "under-review",
        "preprint",
      ]),
    ],
  },
  {
    key: "certifications",
    label: "Certifications",
    singular: "Certification",
    fields: [
      text("name", "Name"),
      text("issuer", "Issuer"),
      date("issueDate", "Issue date"),
      date("expiryDate", "Expiry date"),
      text("credentialId", "Credential ID"),
      url("url", "URL"),
    ],
  },
  {
    key: "skills",
    label: "Skills",
    singular: "Skill",
    fields: [
      text("name", "Skill"),
      text("category", "Category (e.g. languages, frameworks, tools)"),
      text("level", "Proficiency"),
      { path: ["years"], label: "Years of experience", kind: "number" },
    ],
  },
  {
    key: "languages",
    label: "Languages",
    singular: "Language",
    fields: [
      text("language", "Language"),
      choice("proficiency", "Proficiency", [
        "native",
        "fluent",
        "professional",
        "conversational",
        "basic",
      ]),
    ],
  },
  {
    key: "awards",
    label: "Awards",
    singular: "Award",
    fields: [
      text("title", "Title"),
      text("issuer", "Issuer"),
      date("date", "Date"),
      ...description,
    ],
  },
  {
    key: "volunteering",
    label: "Volunteering",
    singular: "Volunteering role",
    fields: [
      text("organisation", "Organisation"),
      text("role", "Role"),
      ...span,
      ...description,
      aliases,
    ],
  },
  {
    key: "courses",
    label: "Courses",
    singular: "Course",
    fields: [
      text("name", "Name"),
      text("provider", "Provider"),
      date("completionDate", "Completed"),
    ],
  },
  {
    key: "memberships",
    label: "Memberships",
    singular: "Membership",
    fields: [
      text("organisation", "Organisation"),
      text("level", "Membership level"),
      date("start", "Since"),
    ],
  },
  {
    key: "talks",
    label: "Talks",
    singular: "Talk",
    fields: [
      text("title", "Title"),
      text("event", "Event"),
      date("date", "Date"),
      url("url", "URL"),
    ],
  },
  {
    key: "patents",
    label: "Patents",
    singular: "Patent",
    fields: [
      text("title", "Title"),
      text("number", "Number"),
      text("status", "Status"),
      date("date", "Date"),
    ],
  },
  {
    key: "references",
    label: "References",
    singular: "Reference",
    fields: [
      text("name", "Name"),
      text("title", "Job title"),
      text("organisation", "Organisation"),
      { path: ["email"], label: "Email", kind: "email" },
      text("phone", "Phone"),
      text("relationship", "Relationship"),
    ],
  },
];

export const SECTION_LABELS: Record<string, string> = {
  personal: "Personal details",
  summary: "Summary",
  ...Object.fromEntries(LISTS.map((s) => [s.key, s.label])),
};
