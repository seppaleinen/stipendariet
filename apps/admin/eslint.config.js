import stipendarietConfig from "@stipendariet/eslint-config";

export default [
  ...stipendarietConfig,
  // Test idioms: mocks legitimately use `any`; hooks may be called inside
  // expect() callbacks (renderHook-style assertions).
  {
    files: ["**/*.test.{ts,tsx}", "**/*.spec.{ts,tsx}"],
    rules: {
      "react-hooks/rules-of-hooks": "off",
      "@typescript-eslint/no-explicit-any": "off",
    },
  },
  // Vendored shadcn/Radix primitives kept verbatim for upstream diffability:
  // badge/button export variants beside components, input declares an empty
  // interface extending native props, toaster re-exports toast helpers.
  {
    files: ["src/components/ui/**"],
    rules: {
      "react-refresh/only-export-components": "off",
      "@typescript-eslint/no-empty-object-type": "off",
    },
  },
  // React context/hook modules conventionally co-export the Provider component
  // and its consumer hook (useAuth); fast-refresh simply cannot HMR such
  // files — no runtime impact.
  {
    files: ["src/hooks/**"],
    rules: {
      "react-refresh/only-export-components": "off",
    },
  },
];
