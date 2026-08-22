import stipendarietConfig from "@stipendariet/eslint-config";

export default [
  ...stipendarietConfig,
  // This package consists entirely of vendored shadcn/Radix primitives kept
  // verbatim for upstream diffability: several files export variants/helpers
  // alongside components, some extend native props via empty interfaces.
  // Unused-var placeholders follow the `_`-prefix convention handled in base.
  {
    files: ["src/**"],
    rules: {
      "react-refresh/only-export-components": "off",
      "@typescript-eslint/no-empty-object-type": "off",
    },
  },
  // Copied shadcn use-toast boilerplate; `actionTypes` is only consumed in a
  // type position. Kept byte-identical to upstream on purpose.
  {
    files: ["src/hooks/use-toast.ts"],
    rules: {
      "@typescript-eslint/no-unused-vars": "off",
    },
  },
];
