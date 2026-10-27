import { useState, useEffect } from "react";
import { getGrants } from "@/lib/api";
import { useSSRData } from "@/contexts/SSRDataContext";
import type { Grant, GrantsResponse } from "../types";

const ITEMS_PER_PAGE = 50;

export function useGrantsList() {
  // Read pre-fetched grants from SSR. Lazy initialisers make this synchronous.
  const ssrData = useSSRData();
  const ssrGrants = (ssrData.grants as GrantsResponse | undefined) ?? null;

  const [grants, setGrants] = useState<Grant[]>(() => ssrGrants?.grants ?? []);
  const [totalCount, setTotalCount] = useState<number>(() => ssrGrants?.total ?? 0);
  const [loading, setLoading] = useState<boolean>(() => ssrGrants == null);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState<boolean>(() => ssrGrants?.has_more ?? true);
  const [searchQuery, setSearchQuery] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [skip, setSkip] = useState<number>(() => ssrGrants?.skip ?? 0);
  const [categories, setCategories] = useState<string[]>(["all"]);

  // Debounce search
  const [debouncedSearch, setDebouncedSearch] = useState("");
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchQuery), 300);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  // If SSR provided an initial grants list, the categories can be extracted from it.
  // Otherwise, fetch on first effect.
  useEffect(() => {
    if (ssrGrants?.grants.length) {
      const uniqueCategories = Array.from(
        new Set(ssrGrants.grants.map((g) => g.category).filter(Boolean))
      );
      setCategories(["all", ...uniqueCategories]);
      return;
    }
    // SSR did not provide grants — fetch the first page
    loadGrants(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentionally omitted: loadGrants closes over `skip`
  }, [debouncedSearch, categoryFilter]);

  const loadGrants = async (reset: boolean = false) => {
    const newSkip = reset ? 0 : skip;
    if (reset) {
      setLoading(true);
      setSkip(0);
    } else {
      setLoadingMore(true);
    }

    try {
      const response = await getGrants({
        search: debouncedSearch || undefined,
        category: categoryFilter !== "all" ? categoryFilter : undefined,
        skip: newSkip,
        limit: ITEMS_PER_PAGE,
      });

      if (reset) {
        setGrants(response.grants);
      } else {
        setGrants((prev) => [...prev, ...response.grants]);
      }
      setTotalCount(response.total);
      setHasMore(response.has_more);
      setSkip(newSkip + response.grants.length);

      // Extract categories from first page load
      if (reset && response.grants.length > 0) {
        const uniqueCategories = Array.from(
          new Set(response.grants.map((g) => g.category).filter(Boolean))
        );
        setCategories(["all", ...uniqueCategories]);
      }
    } catch (error) {
      console.error("Error loading grants:", error);
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  const loadMore = () => {
    if (!loadingMore && hasMore) {
      loadGrants(false);
    }
  };

  // Infinite scroll
  useEffect(() => {
    const handleScroll = () => {
      if (
        window.innerHeight + document.documentElement.scrollTop >=
        document.documentElement.offsetHeight - 200 &&
        !loadingMore &&
        hasMore &&
        !loading
      ) {
        loadMore();
      }
    };

    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- loadMore identity changes every render by design; state flags below already gate the handler
  }, [loadingMore, hasMore, loading]);

  return {
    grants,
    totalCount,
    loading,
    loadingMore,
    hasMore,
    searchQuery,
    setSearchQuery,
    categoryFilter,
    setCategoryFilter,
    categories,
    loadMore,
    refetch: () => loadGrants(true),
  };
}