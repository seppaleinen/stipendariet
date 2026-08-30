import { QueryClient } from "@tanstack/react-query";

// Shared QueryClient instance used by both entry points.
// Kept module-level so it is instantiated once per Node.js process (server entry)
// and once per browser page (client entry).
export const queryClient = new QueryClient();
