Closing the issue — all 9 flaws have been implemented and merged to main.

| SHA | Change |
|-----|--------|
| d643a06 | SSR fallback server + prerender stripped of per-grant loop |
| 10cd4c9 | SSR sidecar added to frontend Helm chart |
| e3e0135 | Sitemap lastmod + image extension via new /api/grants/sitemap-data |
| 770d8ea | sameAs cleaned up, Knowledge Graph fields added, grant detail suppression |
| eabb801 | FAQPage schema matched with visible FAQSection markup on all pages |
| deb4e11 | HowTo + BreadcrumbList on /matching and /grants; QAPage + FAQSection on grant detail |
| e1e6f91 | about, keywords, inLanguage, application dates added to ScholarshipProgram |
| 992efd0 | enriched_description field flows LLM → DB → API → frontend |
| 9a5f8c5 | /api/grants/export.json endpoint + llms.txt build script + nginx cache config |

Final test counts: Frontend 258 / Backend 269 / E2E 17.

Thanks for the clean issue structure — the 3x3 matrix made it easy to sequence.