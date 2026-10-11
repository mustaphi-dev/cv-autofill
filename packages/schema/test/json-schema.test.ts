import { expect, test } from "vitest";
import * as z from "zod";
import { Profile } from "../src/index";

// The backend reads this file (input shape: what the extension accepts).
// CI fails if it drifts from the Zod schema. Until the first release, v1 is
// updated in place with `vitest -u`. After release, a schema change means a
// new schemaVersion, a new file, and a migration (see profile.test.ts).
test("JSON Schema export matches the committed file", async () => {
  const schema = z.toJSONSchema(Profile, { io: "input" });
  await expect(JSON.stringify(schema, null, 2) + "\n").toMatchFileSnapshot(
    "../profile.v1.schema.json",
  );
});
