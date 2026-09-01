import { Helmet } from "react-helmet-async";
import { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { ArrowLeft, ExternalLink, Bookmark, FileText, Phone, MapPin, Users, Mail, CalendarDays } from "lucide-react";
import { Button } from "@stipendariet/ui";
import { Badge } from "@stipendariet/ui";
import {
  Card,
  CardContent,
  CardHeader,
} from "@stipendariet/ui";
import { getGrant, getSavedGrants, saveGrant, removeSavedGrant } from "@/lib/api";
import { formatFoundationText, formatParagraph } from "@/lib/utils";
import { Grant } from "@/types/grants";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";
import { SITE_URL } from "@/lib/page-metadata";
import { useSSRData } from "@/contexts/SSRDataContext";
import FAQSchema from "@/components/FAQSchema";
import { FAQSection } from "@/components/FAQSchema";

export default function GrantDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const { toast } = useToast();

  // Read pre-fetched grant data from the SSR pipeline.
  // The lazy initialiser makes this synchronous — the grant is available on first render
  // without waiting for useEffect.
  const ssrData = useSSRData();
  const [grant, setGrant] = useState<Grant | null>(() => {
    const g = ssrData.grant as Grant | undefined;
    return g ?? null;
  });
  const [loading, setLoading] = useState<boolean>(() => ssrData.grant == null);
  const [isSaved, setIsSaved] = useState(false);
  const [saving, setSaving] = useState(false);

  // If the SSR pipeline provided the grant, we're done. Otherwise fetch from the API.
  useEffect(() => {
    if (id && !ssrData.grant) {
      loadGrant(id);
    }
  }, [id]);

  useEffect(() => {
    if (isAuthenticated && id) {
      fetchSaved(id);
    } else {
      setIsSaved(false);
    }
  }, [isAuthenticated, id]);

  const loadGrant = async (grantId: string) => {
    setLoading(true);
    try {
      const data = await getGrant(grantId);
      setGrant(data || null);
    } catch (error) {
      console.error("Failed to load grant", error);
      setGrant(null);
    } finally {
      setLoading(false);
    }
  };

  const fetchSaved = async (grantId: string) => {
    const ids = await getSavedGrants();
    setIsSaved(ids.includes(grantId));
  };

  const toggleSave = async () => {
    if (!grant || saving) return;
    if (!isAuthenticated) {
      toast({ title: "Inloggning krävs", description: "Logga in för att spara stipendier.", variant: "destructive" });
      return;
    }
    setSaving(true);
    try {
      if (isSaved) {
        await removeSavedGrant(grant.id);
        setIsSaved(false);
      } else {
        await saveGrant(grant.id);
        setIsSaved(true);
      }
    } catch (error) {
      console.error("Error toggling saved grant", error);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <>
        <Helmet>
          <title>Laddar stipendieinformation | StipendieAssistenten</title>
          <meta name="description" content="Laddar information om stipendium..." />
        </Helmet>
        <div className="flex items-center justify-center min-h-[400px]" role="status" aria-live="polite">
          <div className="text-muted-foreground">
            <span className="sr-only">Laddar stipendieinformation, vänligen vänta</span>
            Laddar...
          </div>
        </div>
      </>
    );
  }

  if (!grant) {
    return (
      <>
        <Helmet>
          <title>Stipendium hittades inte | StipendieAssistenten</title>
          <meta name="description" content="Detta stipendium finns inte." />
        </Helmet>
        <div className="text-center py-12">
          <p className="text-muted-foreground mb-4">Stipendium hittades inte</p>
          <Button asChild>
            <Link to="/grants">Tillbaka till stipendier</Link>
          </Button>
        </div>
      </>
    );
  }

  // Get the best description to display — prefer the 150+ word enriched description for LLM citation
  const descriptionText = grant.enrichedDescription || grant.translatedPurpose || grant.purpose || grant.description;

  // Build full address
  const fullAddress = [
    grant.coAddress,
    grant.address,
    [grant.postnr, grant.postort].filter(Boolean).join(" "),
  ].filter(Boolean).join("\n");

  // ScholarshipProgram JSON-LD for rich results and AI ingestion
  // (issue #2, GEO Flaw 2 — entity fields added for LLM citation probability)
  const scholarshipSchema = {
    "@context": "https://schema.org",
    "@type": "ScholarshipProgram",
    name: grant.title,
    description: descriptionText,
    about: grant.purpose || grant.translatedPurpose || descriptionText,
    provider: {
      "@type": "Organization",
      name: grant.provider,
      ...(grant.websiteUrl ? { url: grant.websiteUrl } : {}),
    },
    keywords: grant.tags.join(", "),
    inLanguage: "sv-SE",
    ...(grant.amount
      ? {
          aggregateRating: {
            "@type": "QuantitativeValue",
            value: grant.amount.replace(/[^0-9]/g, "") || undefined,
            unitText: grant.amount,
          },
        }
      : {}),
    ...(grant.deadline ? { expirationDate: grant.deadline } : {}),
    ...(grant.applicationStart ? { applicationStartDate: grant.applicationStart } : {}),
    ...(grant.applicationDeadline ? { applicationDeadline: grant.applicationDeadline } : {}),
    ...(grant.whoCanApply
      ? {
          step: grant.whoCanApply
            .split("\n")
            .filter((s) => s.trim().length > 0)
            .slice(0, 3)
            .map((text) => ({ "@type": "HowToStep", text })),
        }
      : {}),
    url: `${SITE_URL}/grants/${id}`,
  };

  // BreadcrumbList JSON-LD for grant navigation (issue #2, AEO Flaw 3)
  const breadcrumbSchema = {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Hem", item: SITE_URL },
      { "@type": "ListItem", position: 2, name: "Hitta stipendier", item: `${SITE_URL}/grants` },
      { "@type": "ListItem", position: 3, name: grant.title, item: `${SITE_URL}/grants/${grant.id}` },
    ],
  };

   return (
     <>
       <Helmet>
         <title>{`${grant.title} - ${grant.provider} | StipendieAssistenten`}</title>
         <meta name="description" content={grant.enrichedDescription || grant.translatedPurpose || grant.purpose || grant.description || ""} />
         <link rel="canonical" href={`${SITE_URL}/grants/${id}`} />
         <link rel="alternate" hrefLang="sv-SE" href={`${SITE_URL}/grants/${id}`} />
         <link rel="alternate" hrefLang="x-default" href={`${SITE_URL}/grants/${id}`} />
         <meta property="og:title" content={grant.title} />
         <meta property="og:description" content={grant.enrichedDescription || grant.translatedPurpose || grant.purpose || grant.description || ""} />
         <meta property="og:type" content="article" />
         <meta property="og:url" content={`${SITE_URL}/grants/${id}`} />
         <meta property="og:image" content={`${SITE_URL}/og-image.png`} />
         <meta property="og:image:width" content="1200" />
         <meta property="og:image:height" content="630" />
         <meta property="og:image:alt" content={`${grant.title} - ${grant.provider}`} />
         <meta name="twitter:card" content="summary_large_image" />
         <meta name="twitter:site" content="@StipendieAss" />
<script type="application/ld+json">
            {JSON.stringify(scholarshipSchema)}
          </script>
          <script type="application/ld+json">
            {JSON.stringify(breadcrumbSchema)}
          </script>
        </Helmet>
       <article className="max-w-4xl mx-auto space-y-6">
         <Button variant="ghost" className="gap-2" onClick={() => navigate(-1)} aria-label="Gå tillbaka till föregående sida">
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Tillbaka
      </Button>

      <Card>
        <CardHeader>
          <div className="flex items-start justify-between mb-4">
            <Badge variant="secondary" className="text-base px-3 py-1">
              {grant.category}
            </Badge>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="icon"
                onClick={toggleSave}
                disabled={saving}
                aria-label={isSaved ? `Ta bort ${grant.title} från sparade` : `Spara ${grant.title}`}
              >
                {isSaved ? (
                  <Bookmark className="h-4 w-4 fill-current" aria-hidden="true" />
                ) : (
                  <Bookmark className="h-4 w-4" aria-hidden="true" />
                )}
              </Button>
            </div>
          </div>

          <h1 className="text-3xl font-bold">{grant.title}</h1>
          <p className="text-muted-foreground mt-2">{grant.provider}</p>
        </CardHeader>

        <CardContent className="space-y-6">
          {/* Key Information — semantic <dl> for LLM/SEO ingestion (issue #23, GEO Flaw 2) */}
          <section aria-labelledby="key-facts-heading">
            <h2 id="key-facts-heading" className="sr-only">Nyckelfakta om stipendium</h2>
            <dl className="grid md:grid-cols-2 gap-4 p-4 bg-muted/50 rounded-lg">
              {grant.orgnr && (
                <div>
                  <dt className="text-sm text-muted-foreground">Organisationsnummer</dt>
                  <dd className="font-medium" data-fresh="true">{grant.orgnr}</dd>
                </div>
              )}
              {grant.amount && (
                <div>
                  <dt className="text-sm text-muted-foreground">Belopp</dt>
                  <dd className="font-medium" data-fresh="true">{grant.amount}</dd>
                </div>
              )}
              {grant.deadline && (
                <div>
                  <dt className="text-sm text-muted-foreground">Ansökningsdeadline</dt>
                  <dd
                    className="font-medium"
                    data-deadline={grant.deadline}
                    data-datetime={grant.deadline}
                  >
                    {grant.deadline}
                  </dd>
                </div>
              )}
              <div>
                <dt className="text-sm text-muted-foreground">Typ</dt>
                <dd className="font-medium">
                  {grant.isRecurring ? "Återkommande" : "Engångsbelopp"}
                </dd>
              </div>
              {grant.applicationStart && (
                <div>
                  <dt className="text-sm text-muted-foreground">Ansökan öppnar</dt>
                  <dd className="font-medium" data-datetime={grant.applicationStart}>
                    {grant.applicationStart}
                  </dd>
                </div>
              )}
              {grant.category && (
                <div>
                  <dt className="text-sm text-muted-foreground">Kategori</dt>
                  <dd className="font-medium">{grant.category}</dd>
                </div>
              )}
            </dl>
          </section>

          {/* Description/Purpose */}
          <div>
            <h3 className="text-xl font-semibold mb-3">Ändamål</h3>
            <div className="text-muted-foreground leading-relaxed space-y-4">
              {formatFoundationText(descriptionText).map((paragraph, pIndex) => (
                <p key={pIndex}>
                  {formatParagraph(paragraph).map((line, lIndex) => (
                    <span key={lIndex}>
                      {line}
                      {lIndex < formatParagraph(paragraph).length - 1 && <br />}
                    </span>
                  ))}
                </p>
              ))}
            </div>
          </div>

          {/* Application Period/Method (deadline shown in key info above) */}
          {(grant.applicationStart || grant.applicationMethod) && (
            <div>
              <h3 className="text-xl font-semibold mb-3 flex items-center gap-2">
                <CalendarDays className="h-5 w-5" />
                Ansökningsinformation
              </h3>
              <div className="grid md:grid-cols-2 gap-4">
                {grant.applicationStart && (
                  <div>
                    <div className="text-sm text-muted-foreground mb-1">Ansökan öppnar</div>
                    <div className="font-medium">{grant.applicationStart}</div>
                  </div>
                )}
                {grant.applicationMethod && (
                  <div>
                    <div className="text-sm text-muted-foreground mb-1">Ansökningsmetod</div>
                    <div className="font-medium whitespace-pre-line">{grant.applicationMethod}</div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Contact Information */}
          {(fullAddress || grant.phone || grant.contactEmail || grant.contactPhone) && (
            <div>
              <h3 className="text-xl font-semibold mb-3 flex items-center gap-2">
                <MapPin className="h-5 w-5" />
                Kontaktuppgifter
              </h3>
              <div className="grid md:grid-cols-2 gap-4">
                {fullAddress && (
                  <div>
                    <div className="text-sm text-muted-foreground mb-1">Adress</div>
                    <div className="font-medium whitespace-pre-line">{fullAddress}</div>
                  </div>
                )}
                {(grant.phone || grant.contactPhone) && (
                  <div>
                    <div className="text-sm text-muted-foreground mb-1 flex items-center gap-1">
                      <Phone className="h-4 w-4" /> Telefon
                    </div>
                    <div className="font-medium">{grant.phone || grant.contactPhone}</div>
                  </div>
                )}
                {grant.contactEmail && (
                  <div>
                    <div className="text-sm text-muted-foreground mb-1 flex items-center gap-1">
                      <Mail className="h-4 w-4" /> E-post
                    </div>
                    <div className="font-medium">
                      <a href={`mailto:${grant.contactEmail}`} className="hover:underline">
                        {grant.contactEmail}
                      </a>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Signature */}
          {grant.signature && (
            <div>
              <h3 className="text-xl font-semibold mb-3">Firmateckning</h3>
              <p className="text-muted-foreground">{grant.signature}</p>
            </div>
          )}

          {/* Eligibility criteria */}
          {grant.whoCanApply && (
            <div>
              <h3 className="text-xl font-semibold mb-3">Vem kan söka</h3>
              <div className="text-muted-foreground leading-relaxed space-y-4">
                {formatFoundationText(grant.whoCanApply).map((paragraph, pIndex) => (
                  <p key={pIndex}>
                    {formatParagraph(paragraph).map((line, lIndex) => (
                      <span key={lIndex}>
                        {line}
                        {lIndex < formatParagraph(paragraph).length - 1 && <br />}
                      </span>
                    ))}
                  </p>
                ))}
              </div>
            </div>
          )}

          {/* Roles/People */}
          {grant.roles && grant.roles.length > 0 && (
            <div>
              <h3 className="text-xl font-semibold mb-3 flex items-center gap-2">
                <Users className="h-5 w-5" />
                Funktionärer
              </h3>
              <div className="grid md:grid-cols-2 gap-2">
                {grant.roles.map((role, index) => (
                  <div key={index} className="p-3 bg-muted/50 rounded-lg">
                    <div className="font-medium">{role.name || "Namn saknas"}</div>
                    <div className="text-sm text-muted-foreground">{role.type || "Funktion ej angiven"}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tags */}
          {grant.tags && grant.tags.length > 0 && (
            <div>
              <h3 className="text-xl font-semibold mb-3">Kategorier</h3>
              <div className="flex flex-wrap gap-2">
                {grant.tags.map((tag) => (
                  <Badge key={tag} variant="outline">
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* FAQ JSON-LD (applying topic) — self-mounts via Helmet */}
      <FAQSchema topic="applying" />

      {/* FAQ visible section — below grant details card, above CTA */}
      <FAQSection topic="applying" />

      {/* CTA — outside the card, below FAQ */}
      <div className="flex flex-col sm:flex-row gap-4">
        <Button asChild className="flex-1 gap-2">
          <Link to={`/generate/${id}`}>
            <FileText className="h-4 w-4" />
            Starta Ansökan
          </Link>
        </Button>
        {grant.websiteUrl && (
          <Button asChild variant="outline" className="flex-1 gap-2">
            <a
              href={grant.websiteUrl}
              target="_blank"
              rel="noopener noreferrer"
            >
              <ExternalLink className="h-4 w-4" />
              Besök Webbplats
            </a>
          </Button>
        )}
      </div>
    </article>
  </>
  );
}
