import { Helmet } from "react-helmet-async";
import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Sparkles, Copy, Download, Plus, Trash2 } from "lucide-react";
import { FamilyProfile, FamilyMember, Grant } from "@/types/grants";
import { getProfile, getGrant, generateApplicationWithAI } from "@/lib/api";
import { useToast } from "@/hooks/use-toast";
import { SITE_URL } from "@/lib/page-metadata";

type ParsedFormData = {
  family?: {
    municipality?: string;
    adults?: number;
    children?: number;
    maritalStatus?: string;
    email?: string;
    phone?: string;
  };
  children?: Array<{
    age?: number;
    diagnoses?: string[];
  }>;
  economy?: {
    monthlyIncome?: string;
    financialDifficulties?: boolean;
  };
};

export default function Generate() {
  const { id } = useParams();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true); // For initial data load
  const [generatedContent, setGeneratedContent] = useState<string | null>(null);
  const [creditsRemaining, setCreditsRemaining] = useState<number | null>(null);
  const [profile, setProfile] = useState<FamilyProfile>({
    familyMembers: [],
    economicSituation: "",
    goals: "",
    achievements: "",
    background: "",
  });
  const [foundation, setFoundation] = useState<Grant | null>(null);

  // Load existing profile data and foundation details on component mount
  useEffect(() => {
    const loadData = async () => {
      try {
        // Load profile data
        const loadedProfile = await getProfile();
        if (loadedProfile) {
          setProfile(loadedProfile);
        }

        // Load foundation details if an ID is provided
        if (id) {
          const loadedFoundation = await getGrant(id);
          if (loadedFoundation) {
            setFoundation(loadedFoundation);
          }
        }
      } catch (error) {
        console.error("Error loading data:", error);
        // Continue with empty profile if loading fails
      } finally {
        setInitialLoading(false);
      }
    };

    loadData();
  }, [id]);

  const addMember = () => {
    setProfile({
      ...profile,
      familyMembers: [...(profile.familyMembers || []), { name: "", age: 0, role: "" }],
    });
  };

  const removeMember = (index: number) => {
    setProfile({
      ...profile,
      familyMembers: (profile.familyMembers || []).filter((_, i) => i !== index),
    });
  };

  const updateMember = (
    index: number,
    field: keyof FamilyMember,
    value: string | number,
  ) => {
    const updatedMembers = [...(profile.familyMembers || [])];
    updatedMembers[index] = { ...updatedMembers[index], [field]: value };
    setProfile({ ...profile, familyMembers: updatedMembers });
  };

  const handleGenerate = async () => {
    setLoading(true);
    try {
      // Parse detailed form data from profile background if it exists
      let parsedFormData: ParsedFormData | null = null;
      try {
        parsedFormData = JSON.parse(profile.background || "{}");
      } catch (e) {
        // If parsing fails, create a basic form data structure from the profile
        parsedFormData = {
          family: {
            municipality: profile.background?.includes("i ")
              ? profile.background.split("i ")[1]?.split(".")[0] || ""
              : "",
            adults:
              (profile.familyMembers || []).filter(
                (m) => m.role === "Adult" || m.role === "adult",
              ).length || 1,
            children:
              (profile.familyMembers || []).filter(
                (m) => m.role === "Child" || m.role === "child",
              ).length || 0,
            maritalStatus: "single", // default value
            email: "", // default value
            phone: "", // default value
          },
          children: (profile.familyMembers || [])
            .filter((m) => m.role === "Child" || m.role === "child")
            .map((child) => ({
              age: child.age,
              // Since we don't have detailed diagnosis data in basic FamilyMember,
              // we'll need to make do with basic info
              diagnoses: [],
              otherDiagnosis: "",
              needLevel: "0",
              mobility: {
                wheelchair: false,
                assistiveDevices: "",
                stairs: false,
                supervision: false,
              },
            })),
          economy: {
            monthlyIncome: profile.economicSituation,
            financialDifficulties:
              profile.achievements?.includes("ekonomiska utmaningar") || false,
          },
        };
      }

      // Extract user information for personalization
      const firstAdult = (profile.familyMembers || []).find(
        (m) => m.role === "Adult" || m.role === "adult",
      );
      const userName = firstAdult?.name || "Familjen";
      const userEmail =
        parsedFormData?.family?.email ||
        profile.background?.match(/Email: ([^,]+)/)?.[1] ||
        "Ej angiven";
      const userPhone =
        parsedFormData?.family?.phone ||
        profile.background?.match(/Telefon: ([^,]+)/)?.[1] ||
        "Ej angiven";

      // Create a detailed prompt for the AI model combining family profile and foundation data
      let prompt =
        "Skriv en personlig och övertygande ansökan på svenska baserat på följande information:\n\n";

      // Add sender information for personalization
      prompt += "Avsändarinformation:\n";
      prompt += `- Namn: ${userName}\n`;
      prompt += `- E-post: ${userEmail}\n`;
      prompt += `- Telefon: ${userPhone}\n\n`;

      // Add family profile information
      prompt += "Familjeprofil:\n";
      prompt += `- Familj med ${
        parsedFormData?.family?.adults ||
        (profile.familyMembers || []).filter(
          (m) => m.role === "Adult" || m.role === "adult",
        ).length
      } vuxna och ${
        parsedFormData?.family?.children ||
        (profile.familyMembers || []).filter(
          (m) => m.role === "Child" || m.role === "child",
        ).length
      } barn\n`;
      if (parsedFormData?.family?.municipality) {
        prompt += `- Bor i ${parsedFormData?.family?.municipality}\n`;
      }

      // Add children details
      if (parsedFormData?.children && parsedFormData.children.length > 0) {
        prompt += "- Barnsdetaljer:\n";
        parsedFormData.children.forEach((child, index: number) => {
          const childAge = child?.age ?? "";
          const diagnoses = child?.diagnoses || [];
          prompt += `  * Barn ${index + 1}: ${childAge} år gammalt`;
          if (diagnoses.length > 0) {
            prompt += `, har ${diagnoses.join(", ")}\n`;
          } else {
            prompt += "\n";
          }
        });
      }

      // Add economic situation
      prompt += `- Ekonomisk situation: ${profile.economicSituation || "Ej angiven"}\n`;
      prompt += `- Mål: ${profile.goals || "Inga specifika mål angivna"}\n`;
      prompt += `- Meriter: ${profile.achievements || "Inga meriter angivna"}\n`;

      // Add foundation information if available
      if (foundation) {
        prompt += `\nStiftelse/Stipendium som söks:\n`;
        prompt += `- Namn: ${foundation.title || foundation.name || "Ej angivet"}\n`;
        prompt += `- Beskrivning: ${foundation.description || "Ej angiven"}\n`;
        if (foundation.summary) {
          prompt += `- Sammanfattning: ${foundation.summary}\n`;
        }
        if (foundation.purpose || foundation.andamal) {
          prompt += `- Ändamål: ${foundation.purpose || foundation.andamal}\n`;
        }
        if (foundation.provider) {
          prompt += `- Utgivare: ${foundation.provider}\n`;
        }
      }

      prompt +=
        "\nINSTRUKTION:\nDu ska agera som en erfaren, svensk bidragsansökan-skrivare med expertis inom finansiering från stiftelser och fonder. Skriv ett personligt, övertygande och professionellt följebrev/ansökan till den specifika stiftelsen med följande stil och struktur:\n\n";
      prompt += "STIL OCH TON:\n";
      prompt +=
        "1. Naturlig svenska: Texten får INTE låta som en översättning från engelska. Undvik uttryck som 'jag hoppas detta brev finner dig väl' eller överdrivna adjektiv.\n";
      prompt +=
        "2. Balans: Var ödmjuk men kompetent. I Sverige uppskattas saklighet. Skryt inte, utan beskriv konkret vilken nytta projektet gör.\n";
      prompt +=
        "3. Artighet: Använd en formell men varm ton. Undvik byråkratiskt 'kanslisvenska'.\n";
      prompt +=
        "4. Struktur: Ämnesraden ska vara tydlig. Inledningen ska fånga intresset direkt.\n\n";
      prompt += "STRUKTUR PÅ MAILET:\n";
      prompt += "- Ämnesrad: Kort, tydlig och relevant för ansökan.\n";
      prompt += "- Hälsningsfras: Formell men inte stel.\n";
      prompt +=
        "- 'Hook': Varför söker jag just DENNA stiftelse? Koppla mitt syfte till deras ändamål.\n";
      prompt +=
        "- Projektet: Vad ska göras? Vem hjälps? Varför behövs pengarna?\n";
      prompt +=
        "- Avslut: Tydlig information om bifogade dokument och en artig, hoppfull hälsning.\n\n";
      prompt +=
        "Ersätt alla platshållare som [Your Name], [Your Contact Information] och Dear [Recipient's Name] med faktiska namn och kontaktuppgifter. Skriv på svenska.";

      if (!foundation?.id) {
        throw new Error("Ingen valt stipendium att generera för");
      }

      const result = await generateApplicationWithAI(foundation.id, prompt);
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
              {foundation.title || foundation.name}
            </h2>
            <p className="text-blue-600">
              {foundation.summary || foundation.description}
            </p>
          </div>
        )}
        <p className="text-muted-foreground">
          {foundation
            ? `Skapa en personlig ansökan till: ${foundation.title || foundation.name || "vald stiftelse"}`
            : "Fyll i din familjeprofil så hjälper vår AI dig att skapa en personlig ansökan"}
        </p>
      </div>

      {initialLoading && (
        <div className="text-center py-8">
          <div className="inline-block h-8 w-8 animate-spin rounded-full border-2 border-current border-t-transparent mx-auto"></div>
          <p className="mt-2">
            Laddar din familjeprofil och stiftelseinformation...
          </p>
        </div>
      )}

      {!initialLoading && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Familjeprofil</CardTitle>
              <CardDescription>
                Information om din familj används för att skapa en skräddarsydd
                ansökan
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Family Members */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <Label className="text-base">Familjemedlemmar</Label>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={addMember}
                    className="gap-2"
                  >
                    <Plus className="h-4 w-4" />
                    Lägg till
                  </Button>
                </div>

                {(profile.familyMembers || []).map((member, index) => (
                  <div
                    key={index}
                    className="grid md:grid-cols-4 gap-4 p-4 border rounded-lg"
                  >
                    <div className="md:col-span-2">
                      <Label htmlFor={`name-${index}`}>Namn</Label>
                      <Input
                        id={`name-${index}`}
                        value={member.name}
                        onChange={(e) =>
                          updateMember(index, "name", e.target.value)
                        }
                        placeholder="Förnamn Efternamn"
                      />
                    </div>
                    <div>
                      <Label htmlFor={`age-${index}`}>Ålder</Label>
                      <Input
                        id={`age-${index}`}
                        type="number"
                        value={member.age || ""}
                        onChange={(e) =>
                          updateMember(
                            index,
                            "age",
                            parseInt(e.target.value) || 0,
                          )
                        }
                        placeholder="25"
                      />
                    </div>
                    <div className="flex gap-2">
                      <div className="flex-1">
                        <Label htmlFor={`role-${index}`}>Roll</Label>
                        <Input
                          id={`role-${index}`}
                          value={member.role}
                          onChange={(e) =>
                            updateMember(index, "role", e.target.value)
                          }
                          placeholder="Förälder/Barn"
                        />
                      </div>
                      {(profile.familyMembers || []).length > 1 && (
                        <Button
                          variant="ghost"
                          size="icon"
                          className="mt-auto"
                          onClick={() => removeMember(index)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Economic Situation */}
              <div>
                <Label htmlFor="economic">Ekonomisk Situation</Label>
                <Textarea
                  id="economic"
                  value={profile.economicSituation}
                  onChange={(e) =>
                    setProfile({
                      ...profile,
                      economicSituation: e.target.value,
                    })
                  }
                  placeholder="Beskriv din familjs ekonomiska situation..."
                  rows={3}
                />
              </div>

              {/* Goals */}
              <div>
                <Label htmlFor="goals">Mål och Ambitioner</Label>
                <Textarea
                  id="goals"
                  value={profile.goals}
                  onChange={(e) =>
                    setProfile({ ...profile, goals: e.target.value })
                  }
                  placeholder="Vad hoppas ni uppnå med stödet?..."
                  rows={3}
                />
              </div>

              {/* Achievements */}
              <div>
                <Label htmlFor="achievements">Prestationer</Label>
                <Textarea
                  id="achievements"
                  value={profile.achievements}
                  onChange={(e) =>
                    setProfile({ ...profile, achievements: e.target.value })
                  }
                  placeholder="Beskriv relevanta prestationer och meriter..."
                  rows={3}
                />
              </div>

              {/* Background */}
              <div>
                <Label htmlFor="background">Bakgrund</Label>
                <Textarea
                  id="background"
                  value={profile.background}
                  onChange={(e) =>
                    setProfile({ ...profile, background: e.target.value })
                  }
                  placeholder="Annan relevant bakgrundsinformation..."
                  rows={3}
                />
              </div>

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

          {generatedContent && (
            <Card>
              <CardHeader>
                <CardTitle>Genererad Ansökan</CardTitle>
                <CardDescription>
                  Granska och redigera texten innan du skickar in din ansökan
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Textarea
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
                  <Button variant="outline" className="gap-2">
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
