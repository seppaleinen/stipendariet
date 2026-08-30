/**
 * SSR data context — provides pre-fetched data to page components during SSR
 * (and on initial client hydration). Pages read synchronously from this context
 * for first-render values; the existing useEffect/useState flows continue to
 * work for client-side refetches and interactions.
 *
 * Why this exists:
 * - renderToString() is synchronous — useState lazy initialisers work, but
 *   async setState calls from useEffect never complete before the SSR HTML is
 *   generated. We need a way to make pre-fetched data visible immediately.
 * - React Query's useQueryClient() works for this, but `setQueryData` + the
 *   page reading the cache synchronously requires a non-trivial refactor of
 *   every page. A simple Context Provider is more surgical.
 *
 * On the SERVER, scripts/prerender.js calls render(url, data) which seeds the
 * context with the pre-fetched data. The pages then read it via useSSRData().
 * On the CLIENT, the context is mounted with `data={}` and the page's existing
 * useEffect/useState flow fetches data as usual.
 */

import { createContext, useContext } from "react";

export type SSRData = {
  /** Pre-fetched grant object for /grants/:id pages. */
  grant?: Record<string, unknown> | null;
  /** Pre-fetched grants list response for /grants. */
  grants?: Record<string, unknown> | null;
};

const SSRDataContext = createContext<SSRData>({});

/** Provider used by both server and client entry points. */
export function SSRDataProvider({
  value,
  children,
}: {
  value: SSRData;
  children: React.ReactNode;
}) {
  return <SSRDataContext.Provider value={value}>{children}</SSRDataContext.Provider>;
}

/**
 * Read pre-fetched SSR data. Always returns an object — empty on the client
 * for non-prerendered navigation, populated on the server for pre-rendered
 * routes.
 */
export function useSSRData(): SSRData {
  return useContext(SSRDataContext);
}