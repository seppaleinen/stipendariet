import { Helmet } from "react-helmet-async";

// ─── Types & Content ─────────────────────────────────────────────────────────

export type FAQTopic = "general" | "search" | "applying";

interface FAQItem {
  q: string;
  a: string;
}

export const FAQ_CONTENT: Record<FAQTopic, FAQItem[]> = {
  general: [
    {
      q: "Vad är StipendieAssistenten?",
      a: "StipendieAssistenten är en gratistjänst som hjälper svenska familjer att hitta och ansöka om stipendier och bidrag. Vi samlar hundratals stipendier i en sökmotor med kraftfulla filter.",
    },
    {
      q: "Är tjänsten gratis?",
      a: "Ja, StipendieAssistenten är helt gratis att använda. Vi finansieras inte av stipendiesökande utan av separata avtal med stiftelser.",
    },
    {
      q: "Vilka stiftelser finns i databasen?",
      a: "Databasen innehåller stipendier från hundratals svenska stiftelser, kommuner, företag och organisationer. Vi uppdaterar kontinuerligt med nya stipendier och tar bort de som inte längre är aktuella.",
    },
    {
      q: "Hur fungerar det?",
      a: "Skapa en profil och svara på frågor om din situation. Vår tjänst hjälper dig hitta stipendier som matchar dina behov baserat på familjesituation, hälsa, yrke och geografiskt område.",
    },
  ],
  search: [
    {
      q: "Hur söker jag bland stipendier?",
      a: "Använd sökfältet för att skriva nyckelord och filtrera efter kategori för att hitta stipendier som passar dig. Du kan också kombinera sökord med kategorier för snävare resultat.",
    },
    {
      q: "Vad betyder kategorierna?",
      a: "Kategorierna grupperar stipendier efter typ och ändamål, till exempel utbildning, idrott, kultur eller familj. Varje stipendium kan tillhöra en eller flera kategorier.",
    },
    {
      q: "Hur ofta uppdateras listan?",
      a: "Vi uppdaterar stipendielistan kontinuerligt. Nya stipendier läggs till varje vecka och stängda stipendier tas bort så snart vi får information om det.",
    },
  ],
  applying: [
    {
      q: "Hur ansöker jag om detta stipendium?",
      a: "Klicka på knappen 'Starta ansökan' på sidan. Den guidade processen hjälper dig att samla information och formulera en stark ansökan.",
    },
    {
      q: "Vad ska min ansökan innehålla?",
      a: "Vanligtvis behöver du skicka in en personlig ansökan, intyg på din situation och ibland rekommendationsbrev. Läs igenom kraven noggrant för varje stipendium.",
    },
    {
      q: "Kan jag spara stipendiet för att ansöka senare?",
      a: "Ja, du kan spara stipendiet genom att klicka på bokmärkesikonen. Logga in för att se dina sparade stipendier och få påminnelser om deadlines.",
    },
  ],
};

// ─── FAQSchema: JSON-LD only ─────────────────────────────────────────────────

export default function FAQSchema({ topic = "general" }: { topic?: FAQTopic }) {
  const faqs = FAQ_CONTENT[topic];

  const schema = {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    mainEntity: faqs.map((item) => ({
      "@type": "Question",
      name: item.q,
      acceptedAnswer: {
        "@type": "Answer",
        text: item.a,
      },
    })),
  };

  return (
    <Helmet>
      <script type="application/ld+json">
        {JSON.stringify(schema)}
      </script>
    </Helmet>
  );
}

// ─── FAQSection: Visible markup ─────────────────────────────────────────────

export function FAQSection({ topic = "general" }: { topic?: FAQTopic }) {
  const faqs = FAQ_CONTENT[topic];

  return (
    <section aria-labelledby="faq-heading">
      <h2 id="faq-heading" className="text-2xl font-bold mb-4">
        Vanliga frågor
      </h2>
      <div className="grid md:grid-cols-2 gap-4">
        {faqs.map((item, index) => (
          <details
            key={index}
            className="rounded-lg border bg-card p-4"
            name={`faq-${topic}`}
          >
            <summary className="cursor-pointer text-base font-medium list-none">
              {item.q}
            </summary>
            <p className="mt-2 text-muted-foreground leading-relaxed">
              {item.a}
            </p>
          </details>
        ))}
      </div>
    </section>
  );
}
