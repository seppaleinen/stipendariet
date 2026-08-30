import { Helmet } from "react-helmet-async";

const FAQ_SCHEMA = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: [
    {
      "@type": "Question",
      name: "Vad är StipendieAssistenten?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "StipendieAssistenten är en gratistjänst som hjälper svenska familjer att hitta och ansöka om stipendier och bidrag. Vi samlar hundratals stipendier i en sökmotor med kraftfulla filter.",
      },
    },
    {
      "@type": "Question",
      name: "Hur hittar jag rätt stipendium?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Skapa en profil och svara på frågor om din situation. Vår AI hjälper dig hitta stipendier som matchar dina behov baserat på familjesituation, hälsa, yrke och geografiskt område.",
      },
    },
    {
      "@type": "Question",
      name: "Vem kan ansöka om stipendier?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "De flesta stipendier riktar sig till specifika grupper: studenter, familjer, personer med funktionsnedsättning, eller personer inom vissa yrken eller branscher. StipendieAssistenten filtrerar fram de stipendier du är kvalificerad för.",
      },
    },
    {
      "@type": "Question",
      name: "Hur ansöker jag om ett stipendium?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Klicka på ett stipendium för att se ansökningsdetaljer och deadline. Du kan använda vår AI-assisterade ansökningshjälp för att skriva en personlig och övertygande ansökan.",
      },
    },
    {
      "@type": "Question",
      name: "Är tjänsten gratis?",
      acceptedAnswer: {
        "@type": "Answer",
        text: "Ja, StipendieAssistenten är helt gratis att använda. Vi finansieras inte av stipendiesökande utan av separata avtal med stiftelser.",
      },
    },
  ],
};

export default function FAQSchema() {
  return (
    <Helmet>
      <script type="application/ld+json">
        {JSON.stringify(FAQ_SCHEMA)}
      </script>
    </Helmet>
  );
}