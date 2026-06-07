import { Helmet } from "react-helmet-async";
import { useState, useEffect, useMemo } from "react";
import { useForm, Controller } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import * as z from "zod";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SITE_URL } from "@/lib/page-metadata";
import {
  MapPin,
  Users,
  Heart,
  Briefcase,
  Target,
  Loader2,
  ChevronRight,
  ChevronLeft,
  Save,
  User
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import { Profile } from "@/lib/api";
import { SWEDISH_REGIONS, findCountyByCode } from "@/data/swedish-regions";
import { useProfile } from "@/contexts/ProfileContext";

// Schema for the structured profile
const profileSetupSchema = z.object({
  name: z.string().min(1, "Namn krävs"),
  // Section 1: Geography
  countyCode: z.string().optional(),
  municipalityCode: z.string().optional(),

  // Section 2: Life Situation
  lifeSituations: z.array(z.string()).optional(),

  // Section 3: Health
  healthConditions: z.array(z.string()).optional(),
  healthDetails: z.string().optional(),

  // Section 4: Occupations
  occupations: z.array(z.string()).optional(),

  // Section 5: Support Purpose
  supportPurposes: z.array(z.string()).optional(),
});

type ProfileSetupForm = z.infer<typeof profileSetupSchema>;

// Option definitions... (Keep existing options)
const LIFE_SITUATION_OPTIONS = [
  { value: "low_income", label: "Låg inkomst", description: "Ekonomiska svårigheter" },
  { value: "single_parent", label: "Ensamstående förälder", description: "Ensam vårdnadshavare" },
  { value: "widow", label: "Änka/änkling", description: "Förlorat make/maka" },
  { value: "pensioner", label: "Pensionär", description: "65+ eller förtidspensionär" },
  { value: "student", label: "Student", description: "Studerande på högskola/universitet" },
  { value: "youth", label: "Ung (under 30)", description: "Ung vuxen" },
  { value: "unemployed", label: "Arbetslös", description: "Arbetssökande" },
];

const HEALTH_CONDITION_OPTIONS = [
  { value: "mobility", label: "Rörelsehinder", description: "Nedsatt rörelseförmåga" },
  { value: "vision_hearing", label: "Syn-/hörselnedsättning", description: "Nedsatt syn eller hörsel" },
  { value: "mental_health", label: "Psykisk ohälsa", description: "Depression, ångest, etc." },
  { value: "allergy", label: "Allergi", description: "Allergier eller överkänslighet" },
  { value: "diabetes", label: "Diabetes", description: "Typ 1 eller 2 diabetes" },
  { value: "cancer", label: "Cancer", description: "Cancersjukdom" },
  { value: "chronic_illness", label: "Kronisk sjukdom", description: "Annan kronisk sjukdom" },
];

const OCCUPATION_OPTIONS = [
  { value: "hotel_restaurant", label: "Hotell & restaurang", description: "Hotell- och restaurangbranschen" },
  { value: "retail", label: "Detaljhandel", description: "Butik och försäljning" },
  { value: "maritime", label: "Sjöfart/fiske", description: "Sjöfart och fiskerinäring" },
  { value: "crafts", label: "Hantverk", description: "Hantverksyrken" },
  { value: "healthcare", label: "Vård & omsorg", description: "Sjukvård och omsorg" },
  { value: "agriculture", label: "Jordbruk/skogsbruk", description: "Lantbruk och skog" },
  { value: "arts", label: "Konst & kultur", description: "Konstnärlig verksamhet" },
  { value: "journalism", label: "Journalistik", description: "Media och skrivande" },
];

const SUPPORT_PURPOSE_OPTIONS = [
  { value: "education", label: "Utbildning", description: "Studier och fortbildning" },
  { value: "financial_aid", label: "Ekonomiskt stöd", description: "Bidrag till livsomkostnader" },
  { value: "health_care", label: "Vård & behandling", description: "Medicinsk vård eller rehabilitering" },
  { value: "projects", label: "Projekt", description: "Verksamhet eller evenemang" },
  { value: "research", label: "Forskning", description: "Vetenskapligt arbete" },
  { value: "travel", label: "Resor", description: "Semester eller resor" },
  { value: "equipment", label: "Utrustning", description: "Hjälpmedel eller utrustning" },
];

const TAB_SECTIONS = [
  { id: "geography", label: "Geografi", icon: MapPin },
  { id: "life", label: "Livssituation", icon: Users },
  { id: "health", label: "Hälsa", icon: Heart },
  { id: "occupation", label: "Yrke", icon: Briefcase },
  { id: "purpose", label: "Ändamål", icon: Target },
];

export default function ProfileSetup() {
  const { activeProfile, updateProfile, isLoading: isProfileLoading } = useProfile();
  const [isSaving, setIsSaving] = useState(false);
  const [activeTab, setActiveTab] = useState("geography");
  const { toast } = useToast();

  const form = useForm<ProfileSetupForm>({
    resolver: zodResolver(profileSetupSchema),
    defaultValues: {
      name: "",
      countyCode: "",
      municipalityCode: "",
      lifeSituations: [],
      healthConditions: [],
      healthDetails: "",
      occupations: [],
      supportPurposes: [],
    },
  });

  const selectedCountyCode = form.watch("countyCode");

  // Get municipalities for selected county
  const municipalities = useMemo(() => {
    if (!selectedCountyCode) return [];
    const county = findCountyByCode(selectedCountyCode);
    return county?.municipalities || [];
  }, [selectedCountyCode]);

  // Reset municipality when county changes
  useEffect(() => {
    const subscription = form.watch((value, { name }) => {
      if (name === "countyCode") {
        form.setValue("municipalityCode", "");
      }
    });
    return () => subscription.unsubscribe();
  }, [form]);

  // Load active profile data
  useEffect(() => {
    if (activeProfile) {
      form.reset({
        name: activeProfile.name || "My Profile",
        countyCode: activeProfile.countyCode || "",
        municipalityCode: activeProfile.municipalityCode || "",
        lifeSituations: activeProfile.lifeSituations || [],
        healthConditions: activeProfile.healthConditions || [],
        healthDetails: activeProfile.healthDetails || "",
        occupations: activeProfile.occupations || [],
        supportPurposes: activeProfile.supportPurposes || [],
      });
    }
  }, [activeProfile, form]);

  const onSubmit = async (data: ProfileSetupForm) => {
    if (!activeProfile?.id) {
       toast({
        title: "Fel",
        description: "Ingen aktiv profil vald.",
        variant: "destructive",
      });
      return;
    }

    setIsSaving(true);
    try {
      const profileData: Profile = {
        id: activeProfile.id, // Keep ID
        name: data.name,
        countyCode: data.countyCode || undefined,
        municipalityCode: data.municipalityCode || undefined,
        lifeSituations: data.lifeSituations || [],
        healthConditions: data.healthConditions || [],
        healthDetails: data.healthDetails || undefined,
        occupations: data.occupations || [],
        supportPurposes: data.supportPurposes || [],
      };

      await updateProfile(activeProfile.id, profileData);
      
      toast({
        title: "Profil sparad",
        description: "Din profil har uppdaterats.",
      });
    } catch (error) {
      console.error("Failed to save profile:", error);
      toast({
        title: "Fel",
        description: "Kunde inte spara profilen. Försök igen.",
        variant: "destructive",
      });
    } finally {
      setIsSaving(false);
    }
  };

  const goToNextTab = () => {
    const currentIndex = TAB_SECTIONS.findIndex(t => t.id === activeTab);
    if (currentIndex < TAB_SECTIONS.length - 1) {
      setActiveTab(TAB_SECTIONS[currentIndex + 1].id);
    }
  };

  const goToPreviousTab = () => {
    const currentIndex = TAB_SECTIONS.findIndex(t => t.id === activeTab);
    if (currentIndex > 0) {
      setActiveTab(TAB_SECTIONS[currentIndex - 1].id);
    }
  };

  const isFirstTab = activeTab === TAB_SECTIONS[0].id;
  const isLastTab = activeTab === TAB_SECTIONS[TAB_SECTIONS.length - 1].id;

  if (isProfileLoading && !activeProfile) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!activeProfile) {
     return (
        <div className="container py-8 text-center">
             <p>Ingen profil vald. Välj en profil i menyn.</p>
        </div>
     );
  }

  return (
    <>
      <Helmet>
        <title>Skapa Profil - StipendieAssistenten</title>
        <meta name="description" content="Skapa din personliga profil för personliga stipendieförslag." />
        <meta name="robots" content="noindex, nofollow" />
        <link rel="canonical" href={`${SITE_URL}/profile-setup`} />
      </Helmet>
      <div className="container max-w-4xl mx-auto py-8 px-4">
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Profil: {activeProfile.name}</h1>
        <p className="text-muted-foreground mt-2">
          Fyll i information för att matcha denna profil mot stiftelser.
        </p>
      </div>

      <form onSubmit={form.handleSubmit(onSubmit)}>
        
        {/* Basic Info */}
        <Card className="mb-6">
             <CardHeader>
                <CardTitle className="flex items-center gap-2">
                   <User className="h-5 w-5" />
                   Grunduppgifter
                </CardTitle>
             </CardHeader>
             <CardContent>
                 <div className="grid gap-4 sm:grid-cols-2">
                     <div className="space-y-2">
                        <Label htmlFor="name">Namn på profil (t.ex. Klient A)</Label>
                        <Input 
                            id="name" 
                            {...form.register("name")} 
                            placeholder="Namn på profil" 
                        />
                        {form.formState.errors.name && (
                            <p className="text-sm text-destructive">{form.formState.errors.name.message}</p>
                        )}
                     </div>
                 </div>
             </CardContent>
        </Card>

        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
          <TabsList className="grid w-full grid-cols-5 gap-2 h-auto p-1">
            {TAB_SECTIONS.map((section) => (
              <TabsTrigger
                key={section.id}
                value={section.id}
                className="flex flex-col items-center gap-1 py-3 data-[state=active]:bg-primary data-[state=active]:text-primary-foreground"
              >
                <section.icon className="h-5 w-5" />
                <span className="text-xs font-medium hidden sm:inline">{section.label}</span>
              </TabsTrigger>
            ))}
          </TabsList>

          {/* Section 1: Geography */}
          <TabsContent value="geography" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MapPin className="h-5 w-5" />
                  Var bor klienten?
                </CardTitle>
                <CardDescription>
                  Många stiftelser riktar sig till personer i specifika län eller kommuner.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="county">Län</Label>
                    <Controller
                      name="countyCode"
                      control={form.control}
                      render={({ field }) => (
                        <Select value={field.value} onValueChange={field.onChange}>
                          <SelectTrigger id="county">
                            <SelectValue placeholder="Välj län..." />
                          </SelectTrigger>
                          <SelectContent>
                            {SWEDISH_REGIONS.map((county) => (
                              <SelectItem key={county.code} value={county.code}>
                                {county.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    />
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="municipality">Kommun</Label>
                    <Controller
                      name="municipalityCode"
                      control={form.control}
                      render={({ field }) => (
                        <Select
                          value={field.value}
                          onValueChange={field.onChange}
                          disabled={!selectedCountyCode}
                        >
                          <SelectTrigger id="municipality">
                            <SelectValue placeholder={selectedCountyCode ? "Välj kommun..." : "Välj först ett län"} />
                          </SelectTrigger>
                          <SelectContent>
                            {municipalities.map((muni) => (
                              <SelectItem key={muni.code} value={muni.code}>
                                {muni.name}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      )}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Section 2: Life Situation */}
          <TabsContent value="life" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Users className="h-5 w-5" />
                  Livssituation
                </CardTitle>
                <CardDescription>
                  Välj de alternativ som stämmer in på situationen.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Controller
                  name="lifeSituations"
                  control={form.control}
                  render={({ field }) => (
                    <div className="grid gap-3 sm:grid-cols-2">
                      {LIFE_SITUATION_OPTIONS.map((option) => (
                        <label
                          key={option.value}
                          className="flex items-start space-x-3 p-3 rounded-lg border cursor-pointer hover:bg-muted/50 transition-colors has-[:checked]:border-primary has-[:checked]:bg-primary/5"
                        >
                          <Checkbox
                            checked={field.value?.includes(option.value)}
                            onCheckedChange={(checked) => {
                                // Explicitly casting to avoid Type complexity in this snippet
                                const val = option.value;
                                const current = field.value || [];
                                if (checked) {
                                    field.onChange([...current, val]);
                                } else {
                                    field.onChange(current.filter((v) => v !== val));
                                }
                            }}
                          />
                          <div className="space-y-0.5">
                            <div className="font-medium">{option.label}</div>
                            <div className="text-sm text-muted-foreground">{option.description}</div>
                          </div>
                        </label>
                      ))}
                    </div>
                  )}
                />
              </CardContent>
            </Card>
          </TabsContent>

          {/* Section 3: Health */}
          <TabsContent value="health" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Heart className="h-5 w-5" />
                  Hälsa & funktionsnedsättning
                </CardTitle>
                <CardDescription>
                  Många stiftelser stödjer personer med specifika hälsotillstånd.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <Controller
                  name="healthConditions"
                  control={form.control}
                  render={({ field }) => (
                    <div className="grid gap-3 sm:grid-cols-2">
                      {HEALTH_CONDITION_OPTIONS.map((option) => (
                        <label
                          key={option.value}
                          className="flex items-start space-x-3 p-3 rounded-lg border cursor-pointer hover:bg-muted/50 transition-colors has-[:checked]:border-primary has-[:checked]:bg-primary/5"
                        >
                          <Checkbox
                            checked={field.value?.includes(option.value)}
                            onCheckedChange={(checked) => {
                                const val = option.value;
                                const current = field.value || [];
                                if (checked) {
                                    field.onChange([...current, val]);
                                } else {
                                    field.onChange(current.filter((v) => v !== val));
                                }
                            }}
                          />
                          <div className="space-y-0.5">
                            <div className="font-medium">{option.label}</div>
                            <div className="text-sm text-muted-foreground">{option.description}</div>
                          </div>
                        </label>
                      ))}
                    </div>
                  )}
                />

                <div className="space-y-2">
                  <Label htmlFor="healthDetails">Övriga detaljer (valfritt)</Label>
                  <Textarea
                    id="healthDetails"
                    placeholder="Beskriv eventuella specifika diagnoser eller hälsotillstånd..."
                    {...form.register("healthDetails")}
                    rows={3}
                  />
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Section 4: Occupation */}
          <TabsContent value="occupation" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Briefcase className="h-5 w-5" />
                  Yrke & bakgrund
                </CardTitle>
                <CardDescription>
                  Vissa stiftelser riktar sig till specifika yrkesgrupper.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Controller
                  name="occupations"
                  control={form.control}
                  render={({ field }) => (
                    <div className="grid gap-3 sm:grid-cols-2">
                      {OCCUPATION_OPTIONS.map((option) => (
                        <label
                          key={option.value}
                          className="flex items-start space-x-3 p-3 rounded-lg border cursor-pointer hover:bg-muted/50 transition-colors has-[:checked]:border-primary has-[:checked]:bg-primary/5"
                        >
                          <Checkbox
                            checked={field.value?.includes(option.value)}
                            onCheckedChange={(checked) => {
                                const val = option.value;
                                const current = field.value || [];
                                if (checked) {
                                    field.onChange([...current, val]);
                                } else {
                                    field.onChange(current.filter((v) => v !== val));
                                }
                            }}
                          />
                          <div className="space-y-0.5">
                            <div className="font-medium">{option.label}</div>
                            <div className="text-sm text-muted-foreground">{option.description}</div>
                          </div>
                        </label>
                      ))}
                    </div>
                  )}
                />
              </CardContent>
            </Card>
          </TabsContent>

          {/* Section 5: Support Purpose */}
          <TabsContent value="purpose" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target className="h-5 w-5" />
                  Vad söker du stöd för?
                </CardTitle>
                <CardDescription>
                  Välj vilken typ av stöd du är intresserad av.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <Controller
                  name="supportPurposes"
                  control={form.control}
                  render={({ field }) => (
                    <div className="grid gap-3 sm:grid-cols-2">
                      {SUPPORT_PURPOSE_OPTIONS.map((option) => (
                        <label
                          key={option.value}
                          className="flex items-start space-x-3 p-3 rounded-lg border cursor-pointer hover:bg-muted/50 transition-colors has-[:checked]:border-primary has-[:checked]:bg-primary/5"
                        >
                          <Checkbox
                            checked={field.value?.includes(option.value)}
                            onCheckedChange={(checked) => {
                                const val = option.value;
                                const current = field.value || [];
                                if (checked) {
                                    field.onChange([...current, val]);
                                } else {
                                    field.onChange(current.filter((v) => v !== val));
                                }
                            }}
                          />
                          <div className="space-y-0.5">
                            <div className="font-medium">{option.label}</div>
                            <div className="text-sm text-muted-foreground">{option.description}</div>
                          </div>
                        </label>
                      ))}
                    </div>
                  )}
                />
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        {/* Navigation and Save */}
        <div className="flex items-center justify-between mt-8 pt-6 border-t">
          <Button
            type="button"
            variant="outline"
            onClick={goToPreviousTab}
            disabled={isFirstTab}
          >
            <ChevronLeft className="h-4 w-4 mr-2" />
            Föregående
          </Button>

          <div className="flex gap-2">
            <Button
              type="submit"
              disabled={isSaving}
            >
              {isSaving ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Sparar...
                </>
              ) : (
                <>
                  <Save className="h-4 w-4 mr-2" />
                  Spara profil
                </>
              )}
            </Button>
          </div>

          <Button
            type="button"
            variant="outline"
            onClick={goToNextTab}
            disabled={isLastTab}
          >
            Nästa
            <ChevronRight className="h-4 w-4 ml-2" />
          </Button>
        </div>
      </form>
    </div>
    </>
  );
}