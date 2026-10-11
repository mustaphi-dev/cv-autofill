import type { Issue } from "@cv-autofill/schema";
import { SECTION_LABELS } from "./fields";

// "fieldOfStudy" -> "field of study"
const words = (key: string) =>
  key.replace(/[A-Z]/g, (c) => ` ${c.toLowerCase()}`);

// Why a value is invalid, in plain words. Never includes the value itself.
export function reason(issue: Issue): string {
  switch (issue.code) {
    case "too_big":
      return `too long (max ${String(issue.maximum)})`;
    case "invalid_format":
      return `not a valid ${issue.format === "regex" ? "value" : issue.format}`;
    case "unrecognized_keys":
      return `unknown field ${issue.keys.map((k) => `"${k}"`).join(", ")}`;
    case "invalid_type":
      return "missing or wrong type";
    default:
      return issue.message;
  }
}

// Where and why, e.g. "Work experience, entry 2, company: too long (max 300)".
export function describeIssue(issue: Issue): string {
  const [section, ...rest] = issue.path;
  // Profile-wide checks (unknown top-level keys, duplicate ids) have no path.
  const where =
    section === undefined
      ? "Profile"
      : [
          SECTION_LABELS[String(section)] ?? words(String(section)),
          ...rest.map((p) =>
            typeof p === "number" ? `entry ${String(p + 1)}` : words(String(p)),
          ),
        ].join(", ");
  return `${where}: ${reason(issue)}`;
}
