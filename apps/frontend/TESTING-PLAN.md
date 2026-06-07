# Testing Plan — StipendieAssistenten Frontend

> **Target:** `stipendium-assistenten-frontend` (Vite + React SPA)
> **Language:** Swedish (sv-SE)
> **Testing Framework:** Vitest + React Testing Library + Playwright

---

## 1. Testing Strategy

### Test Pyramid
```
        / E2E (Playwright) - Main user flows
       /
   Unit (Vitest + RTL) - Complex logic, hooks, utils
  /
Integration (Vitest + RTL) - API layer, contexts, components
```

### Frameworks
| Layer | Tool | Purpose |
|-------|------|---------|
| Unit | Vitest + React Testing Library | Complex functions, hooks, utilities |
| Integration | Vitest + React Testing Library | API layer, contexts, components |
| E2E | Playwright | Main user flows, auth, routing |

---

## 2. Unit Tests

### 2.1 `src/lib/utils.ts`

| Function | Test Cases |
|----------|-----------|
| `cn()` | Merge class names correctly, handle clsx inputs, empty input |
| `formatFoundationText()` | Empty/null input → [], normalize line breaks, unescape slashes/quotes, split paragraphs |
| `formatParagraph()` | Single newlines preserved, trim empty lines |
| `cleanTextForPreview()` | Collapse multiple spaces, replace newlines with space, trim |

### 2.2 `src/lib/api.ts`

| Function | Test Cases |
|----------|-----------|
| `getAuthHeaders()` | With token, without token, Content-Type header |
| `formatDate()` | Valid date → sv-SE format, invalid date → original string, null/undefined |
| `mapGrantFromBackend()` | All field mappings, fallback values, null handling |
| `mapApplicationFromBackend()` | Status mapping, field mappings, fallback values |
| `mapBackendProfileToFrontend()` | Field mappings, legacy vs new naming |
| `mapFrontendProfileToBackend()` | Field mappings, array defaults |

### 2.3 `src/hooks/use-mobile.tsx`

| Hook | Test Cases |
|------|-----------|
| `useIsMobile()` | Returns true on mobile width, false on desktop, handles resize events, cleanup on unmount |

### 2.4 `src/hooks/usePremiumStatus.ts`

| Hook | Test Cases |
|------|-----------|
| `usePremiumStatus()` | Not authenticated → free, valid subscription → premium, credits > 0 → premium, error → free, refresh function works |

### 2.5 `src/lib/page-metadata.ts`

| Function/Constant | Test Cases |
|-------------------|-----------|
| `PAGE_METADATA` | All routes have metadata, correct titles/descriptions, ogImage defined |
| `getGrantMetadata()` | Dynamic grant metadata, truncation at 155 chars, fallback values |

---

## 3. Integration Tests

### 3.1 `src/contexts/AuthContext.tsx`

| Component | Test Cases |
|-----------|-----------|
| `AuthProvider` | Initializes with null user, loads user from localStorage on mount |
| `login()` | Successful login → stores tokens, sets user; Failed login → returns error |
| `logout()` | Clears tokens, sets user to null |
| `signup()` | Successful signup → stores tokens if returned; Failed signup → returns error |
| `refreshUser()` | Refreshes user data, handles 401 → clears tokens |
| `useAuth()` | Throws error when used outside provider |

### 3.2 `src/contexts/ProfileContext.tsx`

| Component | Test Cases |
|-----------|-----------|
| `ProfileProvider` | Loads profiles when authenticated, restores active profile from localStorage |
| `createProfile()` | Calls API, refreshes profiles list |
| `updateProfile()` | Calls API, refreshes profiles list |
| `setActiveProfile()` | Sets active profile, saves to localStorage |
| `refreshProfiles()` | Loads profiles, selects default/first profile |
| `useProfile()` | Throws error when used outside provider |

### 3.3 `src/lib/api.ts` (Integration)

| Function | Test Cases |
|----------|-----------|
| `getGrants()` | Fetches grants, maps from backend, handles pagination, error handling → returns empty array |
| `getGrant()` | Fetches single grant, returns undefined on 404, maps from backend |
| `getSavedGrants()` | Returns saved grant IDs, returns empty on 401 |
| `saveGrant()` | POST request with grant_id, throws on error |
| `removeSavedGrant()` | DELETE request with grantId, throws on error |
| `getApplications()` | Returns applications, handles 401 → empty |
| `createApplication()` | POST application with grant_id and content |
| `updateApplication()` | PUT application with content and status |
| `deleteApplication()` | DELETE application by id |
| `generateApplicationWithAI()` | POST with grant_id and context |
| `findMatchingFoundations()` | POST with needs, threshold, limit |
| `findMatchingFoundationsByProfile()` | POST with profile_id, geo filter, threshold, limit |
| `listProfiles()` | GET profiles |
| `getProfileById()` | GET profile by id |
| `createProfile()` | POST profile |
| `updateProfileById()` | PUT profile |
| `deleteProfile()` | DELETE profile |
| `getProfile()` | GET family profile, handles 401/404 |
| `saveProfile()` | PUT family profile |

### 3.4 Components (Integration)

| Component | Test Cases |
|-----------|-----------|
| `Layout` | Renders nav, renders children, mobile menu toggle |
| `ProtectedRoute` | Renders children when authenticated, redirects when not |
| `SEOHead` | Renders Organization + WebSite structured data (JSON-LD) |
| `NavLink` | Renders link with active state styling |

---

## 4. E2E Tests (Playwright)

### 4.1 Main User Flows

| Flow | Steps |
|------|-------|
| **Home Page** | Visit `/`, verify title and meta tags, verify hero section, verify CTA buttons |
| **Browse Grants** | Visit `/grants`, verify grants list loads, search for a grant, filter by category |
| **Grant Detail** | Visit `/grants/:id`, verify grant details render, verify structured data, verify actions |
| **Matching Page** | Visit `/matching`, verify results load, toggle geo filter, verify results update |
| **Auth Flow** | Visit `/auth`, enter email/password, submit, verify redirect to `/grants` |
| **Save Grant** | Visit `/grants`, click bookmark on a grant, verify saved state |
| **Generate Application** | Visit `/generate/:id`, verify form loads, fill form, submit, verify AI response |
| **Profile Setup** | Visit `/profile-setup`, fill profile fields, submit, verify redirect |
| **Applications Page** | Visit `/applications`, verify applications list loads |

### 4.2 Authenticated Flows (require login)

| Flow | Steps |
|------|-------|
| **Save/Unsave Grant** | Login, visit `/grants`, save a grant, verify bookmark icon, unsave, verify |
| **Generate Application** | Login, visit `/generate/:id`, fill form, submit, verify AI-generated content |
| **Create Profile** | Login, visit `/profile-setup`, fill form, submit, verify success |
| **Edit Profile** | Login, visit `/profile-setup`, edit existing profile, submit, verify |

### 4.3 Protected Routes

| Flow | Steps |
|------|-------|
| **Access Protected Route** | Visit `/applications` without login, verify redirect to `/auth` |
| **Access Protected Route After Login** | Login, visit `/applications`, verify content loads |

### 4.4 SEO Verification

| Flow | Steps |
|------|-------|
| **Meta Tags on Home** | Visit `/`, verify `<title>`, `<meta description>`, `og:*` tags |
| **Meta Tags on Grants** | Visit `/grants`, verify dynamic title and description |
| **Meta Tags on Grant Detail** | Visit `/grants/:id`, verify grant-specific title and description |
| **Noindex on Protected Pages** | Visit `/auth`, verify `<meta name="robots" content="noindex">` |
| **Structured Data** | Visit `/`, verify Organization + WebSite JSON-LD in `<head>` |
| **robots.txt** | Visit `/robots.txt`, verify protected routes are disallowed |
| **sitemap.xml** | Visit `/sitemap.xml`, verify public routes are listed |

### 4.5 Responsive/Responsive

| Flow | Steps |
|------|-------|
| **Mobile Layout** | View `/grants` at mobile width, verify mobile menu works |
| **Desktop Layout** | View `/grants` at desktop width, verify desktop navigation |

---

## 5. Test Configuration

### 5.1 Vitest Setup (`vitest.config.ts`)
```ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react-swc';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    coverage: {
      provider: 'istanbul',
      reporter: ['text', 'json', 'html'],
      exclude: ['node_modules/', 'src/test/', 'src/main.tsx', 'src/vite-env.d.ts'],
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
```

### 5.2 Playwright Setup (`playwright.config.ts`)
```ts
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  testMatch: '**/*.e2e.ts',
  use: {
    baseURL: 'http://localhost:5173',
    headless: true,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
  ],
});
```

### 5.3 Test Setup (`src/test/setup.ts`)
```ts
import '@testing-library/jest-dom';
import { vi } from 'vitest';

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
  })),
});

// Mock fetch
global.fetch = vi.fn();
```

---

## 6. Test File Structure

```
src/
  lib/
    __tests__/
      utils.test.ts          # Unit tests for utils.ts
      api.test.ts            # Unit tests for api.ts mappings
      page-metadata.test.ts  # Unit tests for page-metadata.ts
  hooks/
    __tests__/
      use-mobile.test.tsx    # Unit tests for use-mobile
      usePremiumStatus.test.tsx # Unit tests for usePremiumStatus
  contexts/
    __tests__/
      AuthContext.test.tsx   # Integration tests for AuthContext
      ProfileContext.test.tsx # Integration tests for ProfileContext
  components/
    __tests__/
      Layout.test.tsx        # Integration tests for Layout
      ProtectedRoute.test.tsx # Integration tests for ProtectedRoute
      SEOHead.test.tsx       # Integration tests for SEOHead
      NavLink.test.tsx       # Integration tests for NavLink
  pages/
    __tests__/
      Home.test.tsx          # Integration tests for Home page
      Grants.test.tsx        # Integration tests for Grants page
      Matching.test.tsx      # Integration tests for Matching page
      GrantDetail.test.tsx   # Integration tests for GrantDetail page
      Generate.test.tsx      # Integration tests for Generate page
e2e/
  home.e2e.ts               # E2E tests for home page
  grants.e2e.ts             # E2E tests for grants page
  matching.e2e.ts           # E2E tests for matching page
  auth.e2e.ts               # E2E tests for auth flow
  generate.e2e.ts           # E2E tests for generate flow
  seo.e2e.ts                # E2E tests for SEO verification
  responsive.e2e.ts         # E2E tests for responsive layouts
```

---

## 7. Implementation Priority

### Phase 1: Unit Tests (Week 1)
- [ ] `src/lib/utils.test.ts` — formatFoundationText, cleanTextForPreview, etc.
- [ ] `src/lib/api.test.ts` — mapping functions (mapGrantFromBackend, etc.)
- [ ] `src/lib/page-metadata.test.ts` — PAGE_METADATA, getGrantMetadata
- [ ] `src/hooks/use-mobile.test.tsx` — useIsMobile
- [ ] `src/hooks/usePremiumStatus.test.tsx` — usePremiumStatus

### Phase 2: Integration Tests (Week 2)
- [ ] `src/contexts/AuthContext.test.tsx` — login, logout, signup, refresh
- [ ] `src/contexts/ProfileContext.test.tsx` — create, update, setActive
- [ ] `src/lib/api.test.ts` — API functions (getGrants, getGrant, etc.)
- [ ] `src/components/Layout.test.tsx` — nav, mobile menu
- [ ] `src/components/ProtectedRoute.test.tsx` — auth redirect
- [ ] `src/components/SEOHead.test.tsx` — structured data
- [ ] `src/pages/Home.test.tsx` — hero, CTAs
- [ ] `src/pages/Grants.test.tsx` — search, filter, pagination

### Phase 3: E2E Tests (Week 3)
- [ ] `e2e/home.e2e.ts` — home page verification
- [ ] `e2e/grants.e2e.ts` — browse, search, filter
- [ ] `e2e/matching.e2e.ts` — matching results, geo filter
- [ ] `e2e/auth.e2e.ts` — login flow
- [ ] `e2e/generate.e2e.ts` — application generation
- [ ] `e2e/seo.e2e.ts` — meta tags, structured data, robots.txt, sitemap
- [ ] `e2e/responsive.e2e.ts` — mobile/desktop layouts

---

## 8. Coverage Targets

| Metric | Target |
|--------|--------|
| Line coverage | ≥ 80% |
| Branch coverage | ≥ 75% |
| Function coverage | ≥ 85% |
| E2E coverage | All main user flows |

---

## 9. CI/CD Integration

### GitHub Actions Workflow (`.github/workflows/test.yml`)
```yaml
name: Tests
on: [push, pull_request]
jobs:
  unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
      - run: npm ci
      - run: npm run test:unit
      - run: npm run test:unit:coverage
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 22
      - run: npm ci
      - run: npm run build
      - run: npm run preview &
      - run: npx playwright test
```

---

## 10. Notes

- All tests should be written in Swedish where UI text is involved (e.g., button labels, error messages)
- Use `vi.fn()` for mocking API calls, `vi.spyOn()` for spying on function calls
- Use `@testing-library/react` for component testing (user events, queries)
- Use `@playwright/test` for E2E (browser automation, assertions)
- Mock `fetch` for API tests — never call real API in unit/integration tests
- Use `msw` (Mock Service Worker) for more realistic API mocking if needed
- Test error handling paths (network errors, 401, 404, etc.)
- Test edge cases (empty state, null values, loading states)
