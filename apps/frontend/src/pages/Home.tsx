import { Helmet } from "react-helmet-async";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Search, FileText, Sparkles, ArrowRight, User } from "lucide-react";
import { SITE_URL } from "@/lib/page-metadata";

export default function Home() {
  return (
    <>
      <Helmet>
        <title>StipendieAssistenten - Hitta och ansök om stipendier</title>
        <meta name="description" content="Din guide till att hitta och ansöka om stipendier och bidrag för din familj. Sök bland hundratals stipendier med kraftfulla filter." />
        <link rel="canonical" href={SITE_URL} />
        <meta property="og:title" content="StipendieAssistenten - Hitta och ansök om stipendier" />
        <meta property="og:description" content="Din guide till att hitta och ansöka om stipendier och bidrag för din familj." />
        <meta property="og:type" content="website" />
        <meta property="og:url" content={SITE_URL} />
        <meta name="twitter:card" content="summary_large_image" />
        <meta name="twitter:site" content="@StipendieAss" />
      </Helmet>
      <div className="space-y-12">
      {/* Hero Section */}
      <section className="text-center space-y-4 py-12">
        <h1 className="text-4xl md:text-5xl font-bold tracking-tight">
          Välkommen till StipendieAssistenten
        </h1>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
          Din guide till att hitta och ansöka om stipendier och bidrag
        </p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
          <Button asChild size="lg" className="gap-2">
            <Link to="/profile-setup">
              <User className="h-5 w-5" />
              Skapa profil
            </Link>
          </Button>
          <Button asChild variant="outline" size="lg" className="gap-2">
            <Link to="/grants">
              <Search className="h-5 w-5" />
              Utforska Stipendier
            </Link>
          </Button>
        </div>
      </section>

      {/* Features */}
      <section className="grid md:grid-cols-4 gap-6">
        <Card className="hover:shadow-lg transition-shadow">
          <CardHeader>
            <div className="h-12 w-12 rounded-lg bg-blue-500/10 flex items-center justify-center mb-4">
              <User className="h-6 w-6 text-blue-600" />
            </div>
            <CardTitle>Personlig Profil</CardTitle>
            <CardDescription>
              Skapa din personliga profil för personliga stipendieförslag baserat
              på dina behov
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link
              to="/profile-setup"
              className="text-primary hover:underline flex items-center gap-1"
            >
              Kom igång <ArrowRight className="h-4 w-4" />
            </Link>
          </CardContent>
        </Card>
        <Card className="hover:shadow-lg transition-shadow">
          <CardHeader>
            <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4">
              <Search className="h-6 w-6 text-primary" />
            </div>
            <CardTitle>Hitta Stipendier</CardTitle>
            <CardDescription>
              Sök bland hundratals stipendier och bidrag med kraftfulla filter
              och sortering
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link
              to="/grants"
              className="text-primary hover:underline flex items-center gap-1"
            >
              Börja söka <ArrowRight className="h-4 w-4" />
            </Link>
          </CardContent>
        </Card>

        <Card className="hover:shadow-lg transition-shadow">
          <CardHeader>
            <div className="h-12 w-12 rounded-lg bg-success/10 flex items-center justify-center mb-4">
              <FileText className="h-6 w-6 text-success" />
            </div>
            <CardTitle>Spåra Ansökningar</CardTitle>
            <CardDescription>
              Håll koll på alla dina ansökningar och få påminnelser när du kan
              ansöka igen
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link
              to="/applications"
              className="text-primary hover:underline flex items-center gap-1"
            >
              Se ansökningar <ArrowRight className="h-4 w-4" />
            </Link>
          </CardContent>
        </Card>

        <Card className="hover:shadow-lg transition-shadow">
          <CardHeader>
            <div className="h-12 w-12 rounded-lg bg-accent/10 flex items-center justify-center mb-4">
              <Sparkles className="h-6 w-6 text-accent" />
            </div>
            <CardTitle>AI-Assisterad Ansökan</CardTitle>
            <CardDescription>
              Låt vår AI hjälpa dig skriva personliga och övertygande
              ansökningar
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link
              to="/generate"
              className="text-primary hover:underline flex items-center gap-1"
            >
              Prova nu <ArrowRight className="h-4 w-4" />
            </Link>
          </CardContent>
        </Card>
      </section>
    </div>
    </>
  );
}
