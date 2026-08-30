/**
 * SSR entry point — used by scripts/prerender.js to pre-render public routes.
 *
 * Each call to render() creates a fresh React tree with a new QueryClient
 * seeded with data, then renders to a string via StaticRouter + HelmetProvider.
 */

import { renderToString } from "react-dom/server";
import { StaticRouter } from "react-router-dom/server";
import { HelmetProvider } from "react-helmet-async";
import { createElement } from "react";
import App from "./App";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type HelmetContext = Record<string, any>;

export type RenderResult = {
  html: string;
  head: string;
};

export type PageData = {
  /** Full Grant object — passed as ssrData so GrantDetail renders without re-fetching */
  grant?: Record<string, unknown>;
  /** GrantsResponse for the listing page */
  grants?: Record<string, unknown>;
};

/**
 * Render a URL to static HTML.
 *
 * @param url   The pathname to render (e.g. "/grants/foundation-7994")
 * @param data  Optional page data to seed into SSRDataProvider for the page to read
 */
export async function render(url: string, data: PageData = {}): Promise<RenderResult> {
  const helmetContext: HelmetContext = {};

  const html = renderToString(
    createElement(
      HelmetProvider,
      { context: helmetContext },
      createElement(StaticRouter, { location: url }, createElement(App, { ssrData: data }))
    )
  );

  const head = serializeHead(helmetContext.helmet);
  return { html, head };
}

function serializeHead(helmet?: HelmetContext): string {
  if (!helmet) return "";
  const parts: string[] = [];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const add = (key: string) => { const v = (helmet as any)[key]; if (v?.toString) parts.push(v.toString()); };
  add("title");
  add("meta");
  add("link");
  add("script");
  return parts.join("\n");
}
