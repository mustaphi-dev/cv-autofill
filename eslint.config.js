import js from "@eslint/js";
import comments from "@eslint-community/eslint-plugin-eslint-comments/configs";
import tseslint from "typescript-eslint";

export default tseslint.config(
  { ignores: ["**/coverage/", "backend/"] },
  js.configs.recommended,
  tseslint.configs.strictTypeChecked,
  comments.recommended,
  {
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
    linterOptions: { reportUnusedDisableDirectives: "error" },
    rules: {
      // Spec section 13: a non-null assertion needs a comment explaining why.
      "@eslint-community/eslint-comments/require-description": "error",
    },
  },
  { files: ["**/*.js"], extends: [tseslint.configs.disableTypeChecked] },
);
