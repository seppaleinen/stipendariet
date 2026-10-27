import { Button } from "@stipendariet/ui";
import { GrantCard } from "./GrantCard";
import type { Grant } from "../types";

interface GrantsResultsProps {
  grants: Grant[];
  totalCount: number;
  loading: boolean;
  loadingMore: boolean;
  hasMore: boolean;
  savedGrantIds: Set<string>;
  savingIds: Set<string>;
  onSaveToggle: (grantId: string, shouldSave: boolean) => void;
  loadMore: () => void;
}

export function GrantsResults({
  grants,
  totalCount,
  loading,
  loadingMore,
  hasMore,
  savedGrantIds,
  savingIds,
  onSaveToggle,
  loadMore,
}: GrantsResultsProps) {
  if (loading) {
    return (
      <div className="text-center py-12 text-muted-foreground" role="status" aria-live="polite">
        <span className="sr-only">Laddar stipendier, vänligen vänta</span>
        Laddar stipendier...
      </div>
    );
  }

  if (grants.length === 0) {
    return (
      <div className="text-center py-12 text-muted-foreground" role="status" aria-live="polite">
        Inga stipendier hittades. Prova att ändra dina sökkriterier.
      </div>
    );
  }

  return (
    <>
      <div className="text-sm text-muted-foreground" role="status" aria-live="polite">
        {totalCount.toLocaleString("sv-SE")} stipendier hittades ({grants.length} visas)
      </div>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {grants.map((grant) => (
          <GrantCard
            key={grant.id}
            grant={grant}
            isSaved={savedGrantIds.has(grant.id)}
            isSaving={savingIds.has(grant.id)}
            onSaveToggle={onSaveToggle}
          />
        ))}
      </div>

      {/* Load more */}
      {hasMore && (
        <div className="flex justify-center pt-4">
          <Button
            onClick={loadMore}
            disabled={loadingMore}
            variant="outline"
          >
            {loadingMore ? "Laddar fler..." : "Ladda fler"}
          </Button>
        </div>
      )}
    </>
  );
}