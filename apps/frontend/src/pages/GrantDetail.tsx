import { Helmet } from "react-helmet-async";
import { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { ArrowLeft, ExternalLink, Bookmark, FileText, Phone, MapPin, Users } from "lucide-react";
import { Button } from "@stipendariet/ui";
import { Badge } from "@stipendariet/ui";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@stipendariet/ui";
import { getGrant, getSavedGrants, saveGrant, removeSavedGrant } from "@/lib/api";
import { formatFoundationText, formatParagraph } from "@/lib/utils";
import { Grant } from "@/types/grants";
import { useAuth } from "@/contexts/AuthContext";
import { SITE_URL } from "@/lib/page-metadata";

export default function GrantDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [grant, setGrant] = useState<Grant | null>(null);
  const [loading, setLoading] = useState(true);
  const [isSaved, setIsSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const { isAuthenticated } = useAuth();

  useEffect(() => {
    if (id) {
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
    const data = await getGrant(grantId);
    setGrant(data || null);
    setLoading(false);
  };

  const fetchSaved = async (grantId: string) => {
    const ids = await getSavedGrants();
    setIsSaved(ids.includes(grantId));
  };

  const toggleSave = async () => {
    if (!grant || saving) return;
    if (!isAuthenticated) {
      alert("Logga in för att spara stipendier.");
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

  // Get the best description to display
  const descriptionText = grant.translatedPurpose || grant.purpose || grant.description;

  // Build full address
  const fullAddress = [
    grant.coAddress,
    grant.address,
    [grant.postnr, grant.postort].filter(Boolean).join(" "),
  ].filter(Boolean).join("\n");

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

   return (
     <>
       <Helmet>
         <title>{`${grant.title} - ${grant.provider} | StipendieAssistenten`}</title>
         <meta name="description" content={grant.translatedPurpose || grant.purpose || grant.description || ""} />
         <link rel="canonical" href={`${SITE_URL}/grants/${id}`} />
         <meta property="og:title" content={grant.title} />
         <meta property="og:description" content={grant.translatedPurpose || grant.purpose || grant.description || ""} />
         <meta property="og:type" content="article" />
         <meta property="og:url" content={`${SITE_URL}/grants/${id}`} />
         <meta name="twitter:card" content="summary_large_image" />
         <meta name="twitter:site" content="@StipendieAss" />
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
          {/* Key Information */}
          <div className="grid md:grid-cols-2 gap-4 p-4 bg-muted/50 rounded-lg">
            {grant.orgnr && (
              <div>
                <div className="text-sm text-muted-foreground mb-1">Organisationsnummer</div>
                <div className="font-medium">{grant.orgnr}</div>
              </div>
            )}
            {grant.amount && (
              <div>
                <div className="text-sm text-muted-foreground mb-1">Belopp</div>
                <div className="font-medium">{grant.amount}</div>
              </div>
            )}
            {grant.deadline && (
              <div>
                <div className="text-sm text-muted-foreground mb-1">
                  Ansökningsdeadline
                </div>
                <div className="font-medium">{grant.deadline}</div>
              </div>
            )}
            <div>
              <div className="text-sm text-muted-foreground mb-1">Typ</div>
              <div className="font-medium">
                {grant.isRecurring ? "Återkommande" : "Engångsbelopp"}
              </div>
            </div>
          </div>

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

          {/* Contact Information */}
          {(fullAddress || grant.phone) && (
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
                {grant.phone && (
                  <div>
                    <div className="text-sm text-muted-foreground mb-1 flex items-center gap-1">
                      <Phone className="h-4 w-4" /> Telefon
                    </div>
                    <div className="font-medium">{grant.phone}</div>
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

          {/* Actions */}
          <div className="flex flex-col sm:flex-row gap-4 pt-4">
            <Button asChild className="flex-1 gap-2">
              <Link to="/generate">
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
        </CardContent>
      </Card>
    </article>
    </>
  );
}
