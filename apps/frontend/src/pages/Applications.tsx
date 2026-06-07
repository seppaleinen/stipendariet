import { Helmet } from "react-helmet-async";
import { useState, useEffect } from "react";
import { Plus, Clock, CheckCircle2, XCircle } from "lucide-react";
import { Button } from "@stipendariet/ui";
import { Badge } from "@stipendariet/ui";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@stipendariet/ui";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@stipendariet/ui";
import { getApplications } from "@/lib/api";
import { Application } from "@/types/grants";
import { Link } from "react-router-dom";
import { SITE_URL } from "@/lib/page-metadata";

const statusConfig = {
  draft: {
    label: "Utkast",
    icon: Clock,
    color: "text-muted-foreground",
  },
  submitted: { label: "Inskickad", icon: CheckCircle2, color: "text-primary" },
  rejected: { label: "Avslagen", icon: XCircle, color: "text-destructive" },
  approved: { label: "Godkänd", icon: CheckCircle2, color: "text-success" },
};

export default function Applications() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("all");

  useEffect(() => {
    loadApplications();
  }, []);

  const loadApplications = async () => {
    setLoading(true);
    const data = await getApplications();
    setApplications(data);
    setLoading(false);
  };

  const filteredApplications =
    activeTab === "all"
      ? applications
      : applications.filter((app) => app.status === activeTab);

  const getStatusCounts = () => {
    return {
      all: applications.length,
      draft: applications.filter((a) => a.status === "draft").length,
      submitted: applications.filter((a) => a.status === "submitted").length,
      approved: applications.filter((a) => a.status === "approved").length,
      rejected: applications.filter((a) => a.status === "rejected").length,
    };
  };

  const counts = getStatusCounts();

  return (
    <>
      <Helmet>
        <title>Mina Ansökningar - StipendieAssistenten</title>
        <meta name="description" content="Håll koll på alla dina stipendieansökningar och få påminnelser." />
        <meta name="robots" content="noindex, nofollow" />
        <link rel="canonical" href={`${SITE_URL}/applications`} />
      </Helmet>
      <div className="space-y-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <h1 className="text-3xl font-bold">Mina Ansökningar</h1>
        <Button asChild className="gap-2">
          <Link to="/generate">
            <Plus className="h-4 w-4" />
            Ny Ansökan
          </Link>
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-5">
          <TabsTrigger value="all" className="gap-2">
            Alla <Badge variant="secondary">{counts.all}</Badge>
          </TabsTrigger>
          <TabsTrigger value="draft" className="gap-2">
            Utkast <Badge variant="secondary">{counts.draft}</Badge>
          </TabsTrigger>
          <TabsTrigger value="submitted" className="gap-2">
            Inskickad <Badge variant="secondary">{counts.submitted}</Badge>
          </TabsTrigger>
          <TabsTrigger value="approved" className="gap-2">
            Godkänd <Badge variant="secondary">{counts.approved}</Badge>
          </TabsTrigger>
          <TabsTrigger value="rejected" className="gap-2">
            Avslagen <Badge variant="secondary">{counts.rejected}</Badge>
          </TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab} className="mt-6">
          {loading ? (
            <div className="text-center py-12 text-muted-foreground">
              Laddar ansökningar...
            </div>
          ) : filteredApplications.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <p className="text-muted-foreground mb-4">
                  {activeTab === "all"
                    ? "Du har inga ansökningar ännu."
                    : `Inga ansökningar med status "${statusConfig[activeTab as keyof typeof statusConfig]?.label}".`}
                </p>
                <Button asChild>
                  <Link to="/grants">Utforska Stipendier</Link>
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-4">
              {filteredApplications.map((app) => {
                const StatusIcon = statusConfig[app.status].icon;
                return (
                  <Card
                    key={app.id}
                    className="hover:shadow-md transition-shadow"
                  >
                    <CardHeader>
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <CardTitle className="text-xl">
                            {app.grantTitle}
                          </CardTitle>
                          <CardDescription className="flex items-center gap-2 mt-2">
                            <StatusIcon
                              className={`h-4 w-4 ${statusConfig[app.status].color}`}
                            />
                            <span>{statusConfig[app.status].label}</span>
                          </CardDescription>
                        </div>
                        <Badge
                          variant={
                            app.status === "approved" ? "default" : "secondary"
                          }
                          className={statusConfig[app.status].color}
                        >
                          {statusConfig[app.status].label}
                        </Badge>
                      </div>
                    </CardHeader>

                    <CardContent>
                      <div className="grid md:grid-cols-2 gap-4 text-sm">
                        {app.createdAt && (
                          <div>
                            <span className="text-muted-foreground">
                              Skapad:
                            </span>
                            <span className="ml-2 font-medium">
                              {app.createdAt || ""}
                            </span>
                          </div>
                        )}
                        {app.updatedAt && (
                          <div>
                            <span className="text-muted-foreground">
                              Uppdaterad:
                            </span>
                            <span className="ml-2 font-medium">
                              {app.updatedAt}
                            </span>
                          </div>
                        )}
                      </div>

                      {app.notes && (
                        <div className="mt-4 p-3 bg-muted/50 rounded-lg">
                          <p className="text-sm text-muted-foreground">
                            <strong>Anteckningar:</strong> {app.notes}
                          </p>
                        </div>
                      )}

                      <div className="flex gap-2 mt-4">
                        <Button variant="outline" size="sm">
                          Redigera
                        </Button>
                        <Button variant="ghost" size="sm">
                          Visa Detaljer
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
    </>
  );
}
