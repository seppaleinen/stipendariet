import { useState, useEffect, useCallback } from "react";
import { useAuth, getAuthToken } from "@/contexts/AuthContext";

export type PlanType = "free" | "subscription" | "credits";

export interface PremiumStatus {
  isPremium: boolean;
  planType: PlanType;
  creditsRemaining: number | null;
  subscriptionEnd: string | null;
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

export function usePremiumStatus(): PremiumStatus {
  const { isAuthenticated, isLoading: authLoading } = useAuth();
  const [isPremium, setIsPremium] = useState(false);
  const [planType, setPlanType] = useState<PlanType>("free");
  const [creditsRemaining, setCreditsRemaining] = useState<number | null>(null);
  const [subscriptionEnd, setSubscriptionEnd] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPremiumStatus = useCallback(async () => {
    if (!isAuthenticated) {
      setIsPremium(false);
      setPlanType("free");
      setCreditsRemaining(null);
      setSubscriptionEnd(null);
      setIsLoading(false);
      return;
    }

    const token = getAuthToken();
    if (!token) {
      setIsLoading(false);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      const response = await fetch(`${API_BASE_URL}/subscription/status`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        // If endpoint doesn't exist, assume free tier
        if (response.status === 404) {
          setIsPremium(false);
          setPlanType("free");
          setIsLoading(false);
          return;
        }
        throw new Error("Failed to fetch subscription status");
      }

      const data = await response.json();

      // Determine premium status based on response
      // Adjust this logic based on your backend response structure
      const hasPremium = 
        data.plan_type === "subscription" || 
        (data.plan_type === "credits" && (data.credits_remaining ?? 0) > 0);

      setIsPremium(hasPremium);
      setPlanType(data.plan_type || "free");
      setCreditsRemaining(data.credits_remaining ?? null);
      setSubscriptionEnd(data.subscription_end ?? null);
    } catch (err) {
      console.error("Error fetching premium status:", err);
      setError("Kunde inte hämta prenumerationsstatus");
      // Default to free on error
      setIsPremium(false);
      setPlanType("free");
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (!authLoading) {
      fetchPremiumStatus();
    }
  }, [authLoading, fetchPremiumStatus]);

  return {
    isPremium,
    planType,
    creditsRemaining,
    subscriptionEnd,
    isLoading: isLoading || authLoading,
    error,
    refresh: fetchPremiumStatus,
  };
}
