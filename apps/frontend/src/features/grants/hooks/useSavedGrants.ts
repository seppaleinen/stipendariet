import { useState, useEffect } from "react";
import { getSavedGrants, saveGrant, removeSavedGrant } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { useToast } from "@/hooks/use-toast";

export function useSavedGrants() {
  const [savedGrantIds, setSavedGrantIds] = useState<Set<string>>(new Set());
  const [savingIds, setSavingIds] = useState<Set<string>>(new Set());
  const { isAuthenticated } = useAuth();
  const { toast } = useToast();

  useEffect(() => {
    if (isAuthenticated) {
      getSavedGrants().then((ids) => setSavedGrantIds(new Set(ids)));
    } else {
      setSavedGrantIds(new Set());
    }
  }, [isAuthenticated]);

  const toggleSave = async (grantId: string, shouldSave: boolean) => {
    if (savingIds.has(grantId)) return;
    if (!isAuthenticated) {
      toast({ title: "Inloggning krävs", description: "Logga in för att spara stipendier.", variant: "destructive" });
      return;
    }

    setSavingIds(new Set(savingIds).add(grantId));
    try {
      if (shouldSave) {
        await saveGrant(grantId);
        const next = new Set(savedGrantIds);
        next.add(grantId);
        setSavedGrantIds(next);
      } else {
        await removeSavedGrant(grantId);
        const next = new Set(savedGrantIds);
        next.delete(grantId);
        setSavedGrantIds(next);
      }
    } catch (error) {
      console.error("Error toggling saved grant", error);
    } finally {
      const nextSaving = new Set(savingIds);
      nextSaving.delete(grantId);
      setSavingIds(nextSaving);
    }
  };

  return {
    savedGrantIds,
    savingIds,
    toggleSave,
  };
}