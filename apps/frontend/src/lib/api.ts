import { Grant, Application, ChildNeed } from "@/types/grants";
import { getAuthToken } from "@/contexts/AuthContext";
import type { Grant, GrantsResponse, MatchedFoundation, Profile } from "@stipendariet/types";

// Re-export shared types used by components
export type { MatchedFoundation, Profile, GrantsResponse } from "@stipendariet/types";

const API_BASE_URL = import.meta.env.VITE_API_URL || "/api";

type BackendGrant = Record<string, unknown>;
type BackendApplication = Record<string, unknown>;
type BackendFamilyMember = {
  id?: string;
  name?: string;
  age?: number;
  role?: string;
};
type BackendChildNeed = {
  childId?: string;
  child_id?: string;
  diagnoses?: string[];
  needDegree?: number;
  need_degree?: number;
  otherDiagnosis?: string | null;
  other_diagnosis?: string | null;
};

function getAuthHeaders(): HeadersInit {
  const token = getAuthToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  return headers;
}

function formatDate(dateString: string | undefined): string | undefined {
  if (!dateString) return undefined;
  try {
    const date = new Date(dateString);
    return date.toLocaleDateString("sv-SE");
  } catch {
    return dateString;
  }
}

// Grants API
export async function getGrants(params?: {
  category?: string;
  search?: string;
  skip?: number;
  limit?: number;
}): Promise<GrantsResponse> {
  try {
    const query = new URLSearchParams();
    if (params?.category) query.append("category", params.category);
    if (params?.search) query.append("search", params.search);
    if (params?.skip !== undefined) query.append("skip", params.skip.toString());
    if (params?.limit !== undefined) query.append("limit", params.limit.toString());

    const response = await fetch(
      `${API_BASE_URL}/grants${query.toString() ? `?${query.toString()}` : ""}`,
    );
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    const grantsArray = Array.isArray(data) ? data : data.grants || [];
    return {
      grants: grantsArray.map(mapGrantFromBackend),
      total: data.total || grantsArray.length,
      skip: data.skip || 0,
      limit: data.limit || grantsArray.length,
      has_more: data.has_more || false,
    };
  } catch (error) {
    console.error("Error fetching grants:", error);
    return { grants: [], total: 0, skip: 0, limit: 50, has_more: false };
  }
}

export function mapGrantFromBackend(grant: BackendGrant): Grant {
  const deadline = (grant.deadline || grant.application_deadline) as string | undefined;
  return {
    id: (grant.id as string | number | undefined)?.toString() ?? "",
    title: (grant.name as string) || (grant.title as string) || "Namn saknas",
    summary:
      (grant.summary as string) ||
      (grant.description as string) ||
      "Ingen sammanfattning tillgänglig",
    description:
      (grant.description as string) ||
      (grant.summary as string) ||
      "Ingen beskrivning tillgänglig",
    provider:
      (grant.organization as string) ||
      (grant.provider as string) ||
      "Okänd utgivare",
    amount: (grant.amount as string) || undefined,
    deadline: formatDate(deadline),
    category: (grant.category as string) || "Diverse",
    tags: Array.isArray(grant.tags) ? (grant.tags as string[]) : [],
    isRecurring: grant.cadence
      ? String(grant.cadence).toLowerCase().includes("år")
      : false,
    websiteUrl:
      (grant.link as string) || (grant.website_url as string) || undefined,
    orgnr: (grant.orgnr as string) || undefined,
    purpose: (grant.purpose as string) || undefined,
    translatedPurpose: (grant.translated_purpose as string) || undefined,
    address: (grant.address as string) || undefined,
    postnr: (grant.postnr as string) || undefined,
    postort: (grant.postort as string) || undefined,
    coAddress: (grant.co_address as string) || undefined,
    phone: (grant.phone as string) || undefined,
    signature: (grant.signature as string) || undefined,
    roles: Array.isArray(grant.roles) ? grant.roles : undefined,
  };
}

export async function getGrant(id: string): Promise<Grant | undefined> {
  try {
    const response = await fetch(`${API_BASE_URL}/grants/${id}`);
    if (!response.ok) {
      if (response.status === 404) return undefined;
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const grantData = await response.json();
    return mapGrantFromBackend(grantData);
  } catch (error) {
    console.error("Error fetching grant:", error);
    return undefined;
  }
}

export async function getSavedGrants(): Promise<string[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/profile/saved-grants`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      if (response.status === 401) return [];
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return Array.isArray(data.saved_grants) ? data.saved_grants : [];
  } catch (error) {
    console.error("Error fetching saved grants:", error);
    return [];
  }
}

export async function saveGrant(grantId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/profile/saved-grants`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ grant_id: grantId }),
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
}

export async function removeSavedGrant(grantId: string): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/profile/saved-grants/${grantId}`,
    {
      method: "DELETE",
      headers: getAuthHeaders(),
    },
  );
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
}

// Applications API
const applicationStatusMap: Record<string, Application["status"]> = {
  draft: "draft",
  submitted: "submitted",
  approved: "approved",
  rejected: "rejected",
};

export async function getApplications(): Promise<Application[]> {
  try {
    const response = await fetch(`${API_BASE_URL}/applications`, {
      headers: getAuthHeaders(),
    });

    if (!response.ok) {
      if (response.status === 401) return [];
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data = await response.json();
    return Array.isArray(data)
      ? data.map(mapApplicationFromBackend)
      : [];
  } catch (error) {
    console.error("Error fetching applications:", error);
    return [];
  }
}

export async function getApplication(
  id: string,
): Promise<Application | undefined> {
  try {
    const response = await fetch(`${API_BASE_URL}/applications/${id}`, {
      headers: getAuthHeaders(),
    });
    if (!response.ok) {
      if (response.status === 404) return undefined;
      if (response.status === 401) return undefined;
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const data = await response.json();
    return mapApplicationFromBackend(data);
  } catch (error) {
    console.error("Error fetching application:", error);
    return undefined;
  }
}

export async function createApplication(
  application: { grantId: string; content?: string },
): Promise<Application> {
  const response = await fetch(`${API_BASE_URL}/applications`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ grant_id: application.grantId, content: application.content }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const data = await response.json();
  return mapApplicationFromBackend(data);
}

export async function updateApplication(
  id: string,
  updates: { content?: string; status?: "draft" | "submitted" },
): Promise<Application> {
  const response = await fetch(`${API_BASE_URL}/applications/${id}`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      content: updates.content,
      status: updates.status,
    }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const data = await response.json();
  return mapApplicationFromBackend(data);
}

export async function deleteApplication(id: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/applications/${id}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
}

export function mapApplicationFromBackend(app: BackendApplication): Application {
  const status = applicationStatusMap[app.status as string] ?? "draft";
  return {
    id: (app.id as string | number | undefined)?.toString() ?? "",
    grantId:
      (app.grant_id as string | number | undefined)?.toString() ||
      (app.grantId as string | undefined) ||
      "",
    grantTitle: (app.grant_name as string) || (app.grantTitle as string) || "",
    status,
    createdAt: app.created_at as string | undefined,
    updatedAt: app.updated_at as string | undefined,
    content: app.content as string | undefined,
  };
}

// Profile API
export function mapBackendProfileToFrontend(backendProfile: any): Profile {
  return {
    id: backendProfile.id,
    name: backendProfile.name,
    isDefault: backendProfile.is_default,
    countyCode: backendProfile.countyCode || backendProfile.county_code,
    municipalityCode: backendProfile.municipalityCode || backendProfile.municipality_code,
    lifeSituations: backendProfile.lifeSituations || backendProfile.life_situations || [],
    healthConditions: backendProfile.healthConditions || backendProfile.health_conditions || [],
    healthDetails: backendProfile.healthDetails || backendProfile.health_details,
    occupations: backendProfile.occupations || [],
    supportPurposes: backendProfile.supportPurposes || backendProfile.support_purposes || [],
    legacyData: backendProfile.legacyData || backendProfile.legacy_data,
  };
}

export function mapFrontendProfileToBackend(profile: Profile): any {
  return {
    name: profile.name,
    is_default: profile.isDefault,
    countyCode: profile.countyCode,
    municipalityCode: profile.municipalityCode,
    lifeSituations: profile.lifeSituations || [],
    healthConditions: profile.healthConditions || [],
    healthDetails: profile.healthDetails,
    occupations: profile.occupations || [],
    supportPurposes: profile.supportPurposes || [],
    legacyData: profile.legacyData,
  };
}

export async function listProfiles(): Promise<Profile[]> {
  const response = await fetch(`${API_BASE_URL}/profile/list`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error("Failed to list profiles");
  const data = await response.json();
  return data.map(mapBackendProfileToFrontend);
}

export async function getProfileById(id: number): Promise<Profile> {
  const response = await fetch(`${API_BASE_URL}/profile/${id}`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error("Failed to get profile");
  const data = await response.json();
  return mapBackendProfileToFrontend(data);
}

export async function createProfile(profile: Profile): Promise<Profile> {
  const response = await fetch(`${API_BASE_URL}/profile/`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(mapFrontendProfileToBackend(profile)),
  });
  if (!response.ok) throw new Error("Failed to create profile");
  const data = await response.json();
  return mapBackendProfileToFrontend(data);
}

export async function updateProfileById(id: number, profile: Profile): Promise<Profile> {
  const response = await fetch(`${API_BASE_URL}/profile/${id}`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify(mapFrontendProfileToBackend(profile)),
  });
  if (!response.ok) throw new Error("Failed to update profile");
  const data = await response.json();
  return mapBackendProfileToFrontend(data);
}

export async function deleteProfile(id: number): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/profile/${id}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error("Failed to delete profile");
}

export async function getProfile(): Promise<Profile | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/profile/family`, {
      headers: getAuthHeaders(),
    });

    if (!response.ok) {
      if (response.status === 401) return null;
      if (response.status === 404) return null;
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const backendProfile = await response.json();
    return mapBackendProfileToFrontend(backendProfile);
  } catch (error) {
    console.error("Error fetching profile:", error);
    return null;
  }
}

export async function saveProfile(
  profile: Profile,
): Promise<Profile> {
  const response = await fetch(`${API_BASE_URL}/profile/family`, {
    method: "PUT",
    headers: getAuthHeaders(),
    body: JSON.stringify(mapFrontendProfileToBackend(profile)),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const saved = await response.json();
  return mapBackendProfileToFrontend(saved);
}

// AI Generation API
export async function generateApplicationWithAI(
  grantId: string,
  additionalContext?: string,
): Promise<{ generated_text: string; credits_remaining: number | null }> {
  const response = await fetch(`${API_BASE_URL}/generate/application`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ grant_id: grantId, additional_context: additionalContext }),
  });

  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  return await response.json();
}

// Semantic Matching API

export async function findMatchingFoundations(
  needs: string,
  threshold: number = 0.3,
  limit: number = 20,
  profileId?: number
): Promise<MatchedFoundation[]> {
  try {
    // Determine which endpoint to use
    // If profileId is passed, we technically should use matching-by-profile if 'needs' was just profile text. 
    // But this function signature suggests 'needs' is explict text.
    // However, the backend logic for `matching` (text based) doesn't use profileId.
    // The `matching-by-profile` endpoint uses the profile from DB.
    
    // Let's assume this function is primarily used for text-based matching (e.g. from the 'Generate' page or simple search).
    // If we want to support profile-based matching here, we might need a separate function or clarify usage.
    
    // BUT! I see `findMatchingFoundations` uses `/foundations/matching`.
    // The matching-by-profile logic is client-side in `Matching.tsx` calling `/foundations/matching-by-profile`.
    
    // So I will just update this function to matching the backend signature if needed, but `/foundations/matching` doesn't take profile_id.
    
    // Wait, `Matching.tsx` has its own fetch call. I should probably refactor that to use `api.ts` eventually.
    // For now I will leave this as is unless I need to change it.
    
    // Actually, I should export a new function for `findMatchingFoundationsByProfile`.
    
    const response = await fetch(`${API_BASE_URL}/foundations/matching`, {
      method: "POST",
      headers: getAuthHeaders(),
      body: JSON.stringify({ needs, threshold, limit }),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("Error finding matching foundations:", error);
    throw error;
  }
}

export async function findMatchingFoundationsByProfile(
  profileId?: number,
  useGeoFilter: boolean = true,
  threshold: number = 0.25,
  limit: number = 100
): Promise<MatchedFoundation[]> {
  const response = await fetch(`${API_BASE_URL}/foundations/matching-by-profile`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      profile_id: profileId,
      use_geographic_filter: useGeoFilter,
      threshold,
      limit,
    }),
  });

  if (!response.ok) {
    // Try to parse error
    try {
        const error = await response.json();
        throw new Error(error.detail || `HTTP error! status: ${response.status}`);
    } catch (e) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
  }

  return await response.json();
}
