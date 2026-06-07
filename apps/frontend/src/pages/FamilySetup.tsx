import { Helmet } from "react-helmet-async";
import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Save, FileText } from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { saveProfile, getProfile } from "@/lib/api";
import { SITE_URL } from "@/lib/page-metadata";

export default function FamilySetup() {
  const { toast } = useToast();
  const [needs, setNeeds] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Load existing profile data on component mount
  useEffect(() => {
    const loadProfile = async () => {
      setIsLoading(true);
      try {
        const profile = await getProfile();
        if (profile?.needs) {
          setNeeds(profile.needs);
        }
      } catch (error) {
        console.error("Error loading profile:", error);
      } finally {
        setIsLoading(false);
      }
    };

    loadProfile();
  }, []);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await saveProfile({
        needs: needs,
      });

      toast({
        title: "Sparat!",
        description: "Din beskrivning har sparats.",
      });
    } catch (error) {
      console.error("Error saving profile:", error);
      toast({
        title: "Fel",
        description: "Kunde inte spara. Försök igen.",
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="max-w-2xl mx-auto flex items-center justify-center min-h-[400px]">
        <p className="text-muted-foreground">Laddar...</p>
      </div>
    );
  }

  return (
    <>
      <Helmet>
        <title>Familjeprofil - StipendieAssistenten</title>
        <meta name="description" content="Skapa och hantera din familjeprofil för stipendieförslag." />
        <meta name="robots" content="noindex, nofollow" />
        <link rel="canonical" href={`${SITE_URL}/family-setup`} />
      </Helmet>
      <div className="max-w-2xl mx-auto space-y-8">
      <div className="text-center space-y-4">
        <h1 className="text-3xl font-bold">Beskriv dina behov</h1>
        <p className="text-muted-foreground">
          Beskriv i fritext varför du söker stipendium eller bidrag. Detta hjälper oss att hitta passande möjligheter för dig.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Din situation
          </CardTitle>
          <CardDescription>
            Beskriv din situation och vad du behöver stöd för. Till exempel:
            ekonomiska svårigheter, studier, konstnärlig verksamhet,
            familjens behov, eller annat.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea
            placeholder="Beskriv din situation och varför du söker bidrag eller stipendium..."
            value={needs}
            onChange={(e) => setNeeds(e.target.value)}
            className="min-h-[200px] resize-y"
          />

          <div className="flex justify-end">
            <Button
              onClick={handleSave}
              disabled={isSaving}
              className="gap-2"
            >
              <Save className="h-4 w-4" />
              {isSaving ? "Sparar..." : "Spara"}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
    </>
  );
}