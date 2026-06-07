# Migration Plan: Vite SPA → Next.js (App Router)

## Goal
Migrate `stipendium-assistenten-frontend` from Vite + React SPA to Next.js (app router) for SSR/SSG, matching bitebase's architecture.

## Why
- **SEO improvement**: SSR/SSG renders content server-side, solving the CSR indexing problem
- **Consistency**: Matches bitebase framework (Next.js + Python FastAPI backend)
- **Performance**: Better LCP, code splitting, image optimization
- **Simpler deployment**: Single Next.js app serves both API proxy and UI

## Scope

### What Changes
1. Replace Vite with Next.js (app router)
2. Convert React Router routes to Next.js App Router pages
3. Convert `react-helmet-async` to Next.js metadata API
4. Update nginx deployment to serve Next.js
5. Add API proxy routes (optional — can keep separate backend)
6. Update build scripts (Dockerfile, CI/CD)

### What Stays
1. Component structure (shadcn/ui, Layout, etc.)
2. State management (React Query, AuthContext, ProfileContext)
3. Backend API (FastAPI, separate service)
4. Existing SEOHead component (can be adapted)
5. Existing page metadata config (adapted to Next.js format)

## Migration Steps

### Phase 1: Setup (Day 1)
1. Initialize Next.js app (app router, TypeScript, Tailwind)
2. Copy existing components, hooks, contexts, lib, types
3. Set up tRPC or fetch-based API calls (matching bitebase pattern)
4. Configure `next.config.js` (images, redirects, proxy)
5. Set up metadata API for SEO (title, description, OG tags)

### Phase 2: Route Conversion (Day 2)
1. Convert public pages:
   - `/` → `app/page.tsx` (Home)
   - `/grants` → `app/grants/page.tsx` (Grants)
   - `/matching` → `app/matching/page.tsx` (Matching)
   - `/grants/[id]` → `app/grants/[id]/page.tsx` (GrantDetail)
   - `/` → `app/not-found.tsx` (NotFound)
2. Convert protected pages:
   - `/auth` → `app/auth/page.tsx`
   - `/applications` → `app/applications/page.tsx`
   - `/generate` → `app/generate/page.tsx`
   - `/profile-setup` → `app/profile-setup/page.tsx`
   - `/family-setup` → `app/family-setup/page.tsx`
3. Implement route-level code splitting (React.lazy + Suspense)
4. Add dynamic metadata per route using Next.js `generateMetadata`

### Phase 3: SEO & Structured Data (Day 3)
1. Convert `react-helmet-async` → Next.js `metadata` API
2. Add dynamic OG images, canonical URLs
3. Add Organization + WebSite structured data (JSON-LD)
4. Add Grant detail pages structured data
5. Generate `sitemap.xml` at build time (Next.js built-in)
6. Add `robots.txt` via Next.js API route

### Phase 4: Deployment & Testing (Day 3-4)
1. Update Dockerfile (nginx → Next.js server)
2. Update deployment scripts
3. Test all routes, SSR, hydration
4. Run Lighthouse audit for Core Web Vitals
5. Submit sitemap to Google Search Console

## Technical Details

### Next.js Configuration
```js
// next.config.js
module.exports = {
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'stipendieassistenten.labb.site' },
    ],
  },
  // API proxy (optional)
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://backend:8000/:path*',
      },
    ];
  },
};
```

### Metadata Example
```tsx
// app/grants/page.tsx
import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Stipendier och Bidrag - Sök bland hundratals stipendier | StipendieAssistenten',
  description: 'Utforska och sök bland hundratals stipendier och bidrag...',
  openGraph: {
    title: 'Stipendier och Bidrag | StipendieAssistenten',
    description: 'Utforska och sök bland hundratals stipendier...',
    type: 'website',
  },
  robots: 'index, follow',
};

export default function GrantsPage() {
  return <Grants />;
}
```

### Dynamic Metadata for Grant Detail
```tsx
// app/grants/[id]/page.tsx
import { Metadata } from 'next';
import { getGrant } from '@/lib/api';

export async function generateMetadata({ params }: { params: { id: string } }): Promise<Metadata> {
  const grant = await getGrant(params.id);
  return {
    title: `${grant.title} - ${grant.provider} | StipendieAssistenten`,
    description: grant.translatedPurpose || grant.purpose || grant.description || '',
    openGraph: { title: grant.title, description: grant.purpose },
    alternates: { canonical: `https://stipendieassistenten.labb.site/grants/${params.id}` },
  };
}
```

### Protected Routes
Use Next.js middleware for auth checks (matching bitebase pattern).

## Risk Assessment

| Risk | Mitigation |
|------|-----------|
| Component compatibility | Most shadcn/ui components are vanilla React — should work |
| React Query → tRPC | Can keep React Query with fetch, or migrate to tRPC |
| Deployment changes | Update Dockerfile, CI/CD pipeline |
| SEO regression | Test all pages before deployment |

## Estimated Effort
- **2-3 days** for full migration
- **1 day** for testing and deployment
- **Total: 3-4 days**

## Post-Migration Checklist
- [ ] All routes render correctly with SSR
- [ ] Meta tags correct per page
- [ ] Structured data validates (Rich Results Test)
- [ ] Lighthouse scores improve (LCP < 2.5s, INP < 200ms, CLS < 0.1)
- [ ] Code splitting verified (smaller bundles)
- [ ] Sitemap generated and submitted to GSC
- [ ] robots.txt correct
- [ ] Protected routes properly secured
- [ ] Mobile responsive (unchanged)
- [ ] Accessibility (ARIA labels, skip links)
- [ ] Core Web Vitals pass
