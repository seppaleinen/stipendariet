// Shared types exported from this package.
// Import in apps via `@stipendariet/types`.

export type Foundation = {
  id: string;
  name: string;
  description?: string;
};

export type Scholarship = {
  id: string;
  title: string;
  description?: string;
  foundationId: string;
  startDate: Date | null;
  endDate: Date | null;
};
