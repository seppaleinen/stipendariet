import { Helmet } from "react-helmet-async";
import { useState, useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { Button } from "@stipendariet/ui";
import { Label } from "@stipendariet/ui";
import { Textarea } from "@stipendariet/ui";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@stipendariet/ui";
import { Sparkles, Copy, Download, UserCircle2 } from "lucide-react";
import type { Grant } from "@/types/grants";
import { getGrant, generateApplicationWithAI } from "@/lib/api";
import { useProfile } from "@/contexts/ProfileContext";
import { buildApplicationPrompt } from "@/lib/prompt-builder";
import { useToast } from "@/hooks/use-toast";
import { SITE_URL } from "@/lib/page-metadata";

export default function Generate() {
  const { id } = useParams();
  const { toast } = useToast();
  const { activeProfile, isLoading: profileLoading } = useProfile();
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true); // For initial grant load
  const [generatedContent, setGeneratedContent] = useState<string | null>(null);
  const [creditsRemaining, setCreditsRemaining] = useState<number | null>(null);
  const [foundation, setFoundation] = useState<Grant | null>(null);

  // Load foundation details if an ID is provided
  useEffect(() => {
    const loadData = async () => {
      try {
        if (id) {
          const loadedFoundation = await getGrant(id);
          if (loadedFoundation) {
            setFoundation(loadedFoundation);
          }
        }
      } catch (error) {
        console.error("Error loading data:", error);
      } finally {
        setInitialLoading(false);
      }
    };

    loadData();
  }, [id]);

  const handleGenerate = async () => {
    if (!activeProfile) return;
    setLoading(true);
    try {
      const prompt = buildApplicationPrompt(activeProfile, foundation);

      const result = await generateApplicationWithAI(foundation?.id ?? "", prompt);
      setGeneratedContent(
        result.generated_text || "Genereringen misslyckades",
      );
      setCreditsRemaining(result.credits_remaining ?? null);
      toast({
        title: "Ansökan genererad!",
        description: "Din personliga ansökan har skapats.",
      });
    } catch (error) {
      console.error("Error generating application:", error);
      toast({
        title: "Fel",
        description: "Kunde inte generera ansökan. Försök igen.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = () => {
    if (generatedContent) {
      navigator.clipboard.writeText(generatedContent);
      toast({
        title: "Kopierat!",
        description: "Ansökan kopierad till urklipp.",
      });
    }
  };

  const exportToFile = () => {
    if (generatedContent) {
      const blob = new Blob([generatedContent], { type: "text/plain;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `ansökan-${foundation?.title || "utkast"}.txt`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    }
  };

  return (
    <>
      <Helmet>
        <title>AI-assisterad Stipendieansökan | StipendieAssistenten</title>
        <meta name="description" content="Låt vår AI hjälpa dig skriva personliga och övertygande stipendieansökningar." />
        <meta name="robots" content="noindex, nofollow" />
        <link rel="canonical" href={`${SITE_URL}/generate`} />
      </Helmet>
      <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold mb-2">Skapa Ansökan</h1>
        {foundation && (
          <div className="mb-4 p-4 bg-blue-50 rounded-lg">
            <h2 className="text-xl font-semibold text-blue-800">
              {foundation.title}
            </h2>
            <p className="text-blue-600">
              {foundation.summary || foundation.description}
            </p>
          </div>
        )}
        <p className="text-muted-foreground">
          {foundation
            ? `Skapa en personlig ansökan till: ${foundation.title}`
            : "Vi använder din profil för att skapa en personlig ansökan"}
        </p>
      </div>

      {initialLoading && (
        <div className="text-center py-8">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-2 border-current border-t-transparent mx-auto"></div>
          <p className="mt-2">
            Laddar stiftelseinformation...
          </p>
        </div>
      )}

      {!initialLoading && (
        <>
          {profileLoading ? (
            <Card>
              <CardContent className="py-8 text-center">
                <div className="inline-block h-8 w-8 animate-spin rounded-full border-2 border-current border-t-transparent mx-auto"></div>
              </CardContent>
            </Card>
          ) : activeProfile ? (
            <Card>
              <CardHeader>
                <CardTitle>Din profil</CardTitle>
                <CardDescription>
                  Ansökan skapas utifrån den strukturerade profilen
                  "{activeProfile.name}". Ändra uppgifterna under
                  Profilinställningar om något ser fel ut.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button
                  onClick={handleGenerate}
                  disabled={loading}
                  className="w-full gap-2"
                  size="lg"
                >
                  {loading ? (
                    <>
                      <div className="h-5 w-5 animate-spin rounded-full border-2 border-current border-t-transparent"></div>
                      {" Genererar..."}
                    </>
                  ) : (
                    <>
                      <Sparkles className="h-5 w-5" />
                      {" Generera Ansökan"}
                    </>
                  )}
                </Button>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle>Ingen profil hittades</CardTitle>
                <CardDescription>
                  Fyll i din profil med bostadsort, livssituation och syfte så
                  kan AI:n skräddarsy din ansökan.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Button asChild variant="outline" className="gap-2">
                  <Link to="/profile-setup">
                    <UserCircle2 className="h-4 w-4" />
                    Skapa din profil
                  </Link>
                </Button>
              </CardContent>
            </Card>
          )}

          {generatedContent && (
            <Card>
              <CardHeader>
                <CardTitle>Genererad Ansökan</CardTitle>
                <CardDescription>
                  Granska och redigera texten innan du skickar in din ansökan
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Label className="sr-only" htmlFor="generated-content">Genererad ansökan</Label>
                <Textarea
                  id="generated-content"
                  value={generatedContent}
                  onChange={(e) => setGeneratedContent(e.target.value)}
                  rows={15}
                  className="font-mono text-sm"
                />
                {creditsRemaining !== null && (
                  <p className="text-sm text-muted-foreground">
                    Återstående krediter: {creditsRemaining}
                  </p>
                )}
                <div className="flex gap-2">
                  <Button
                    onClick={copyToClipboard}
                    variant="outline"
                    className="gap-2"
                  >
                    <Copy className="h-4 w-4" />
                    Kopiera Text
                  </Button>
                  <Button variant="outline" className="gap-2" onClick={exportToFile}>
                    <Download className="h-4 w-4" />
                    Exportera
                  </Button>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
    </>
  );
}
