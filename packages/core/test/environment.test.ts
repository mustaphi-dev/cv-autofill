import { expect, test } from "vitest";

// Core runs in a plain DOM with no extension APIs (spec section 5).
test("runs in a DOM without extension APIs", () => {
  document.body.innerHTML = '<label for="a">Name</label><input id="a">';
  expect(document.querySelector("input")?.labels?.[0]?.textContent).toBe(
    "Name",
  );
  expect("chrome" in globalThis).toBe(false);
  expect("browser" in globalThis).toBe(false);
});
