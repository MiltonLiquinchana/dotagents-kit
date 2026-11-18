import base from "./eslint.config.mjs";

export default [
  ...base,
  {
    files: ["**/*.{ts,tsx}"],
    rules: {
      "no-eval": "error",
      "no-implied-eval": "error",
      "no-new-func": "error",
      "no-debugger": "error",
      complexity: ["error", 10],
    },
  },
];
