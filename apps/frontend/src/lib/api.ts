import { Grant, Application } from "@/types/grants";
import { createApiClient } from "@stipendariet/api-client";
import { getAuthToken } from "@/contexts/AuthContext";
import type { MatchedFoundation, ParsedServiceArea, Profile, GrantsResponse } from "@stipendariet/types";

// Re-export shared types used by components
export type { MatchedFoundation, ParsedServiceArea, Profile, GrantsResponse } from "@stipendariet/types";

const api = createApiClient({
  baseUrl: import.meta.env.VITE_API_URL || "/api",
  getToken: () => getAuthToken(),
});

type BackendGrant = Record<string, unknown>;
type BackendApplication = Record<string, unknown>;

// Raw profile payload from the backend API. Endpoints have historically mixed
// camelCase and snake_case keys, so mappers accept both spellings.
type BackendProfile = {
  id?: number;
  name?: string;
  is_default?: boolean;
  countyCode?: string;
  county_code?: string;
  municipalityCode?: string;
  municipality_code?: string;
  lifeSituations?: Profile["lifeSituations"];
  life_situations?: Profile["lifeSituations"];
  healthConditions?: Profile["healthConditions"];
  health_conditions?: Profile["healthConditions"];
  healthDetails?: Profile["healthDetails"];
  health_details?: Profile["healthDetails"];
  occupations?: Profile["occupations"];
  supportPurposes?: Profile["supportPurposes"];
  support_purposes?: Profile["supportPurposes"];
  selfDescription?: Profile["selfDescription"];
  self_description?: Profile["selfDescription"];
  legacyData?: Profile["legacyData"];
  legacy_data?: Profile["legacyData"];
};

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
  const { data } = await api.get('/grants', params);
  if (!data || typeof data !== 'object' || !Array.isArray(data.grants)) {
    throw new Error("Invalid response format from getGrants");
  }
  const grantsArray = data.grants as BackendGrant[];
  return {
    grants: grantsArray.map(mapGrantFromBackend),
    total: (data.total as number) || grantsArray.length,
    skip: (data.skip as number) || 0,
    limit: (data.limit as number) || grantsArray.length,
    has_more: !!data.has_more,
  };
}

export function mapGrantFromBackend(grant: BackendGrant): Grant {
  const deadline = (grant.deadline || grant.application_deadline) as string | undefined;
  return {
    id: (grant.id as string | number | undefined)?.toString() ?? "",
    title: (grant.name as string) || (grant.title as string) || "Namn saknas",
    summary:
      (grant.summary as string) ||
      (grant.description as string) ||
      "Ingen sammanfattning tillg\u00e4nglig",
    description:
      (grant.description as string) ||
      (grant.summary as string) ||
      "Ingen beskrivning tillg\u00e4nglig",
    provider:
      (grant.organization as string) ||
      (grant.provider as string) ||
      "Ok\u00e4nd utgivare",
    amount: (grant.amount as string) || undefined,
    deadline: formatDate(deadline),
    category: (grant.category as string) || "Okänd",
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
    applicationDeadline:
      (grant.application_deadline as string) || undefined,
    applicationStart: (grant.application_start as string) || undefined,
    applicationMethod: (grant.application_method as string) || undefined,
    contactEmail: (grant.contact_email as string) || undefined,
    contactPhone: (grant.contact_phone as string) || undefined,
    whoCanApply: (grant.who_can_apply as string) || undefined,
    enrichedDescription:
      (grant.enriched_description as string) || undefined,
  };
}

export async function getGrant(id: string): Promise<Grant | undefined> {
  try {
    const { data } = await api.get(`/grants/${id}`);
    return mapGrantFromBackend(data);
  } catch (error) {
    if ((error as { status?: number }).status === 404) return undefined;
    throw error;
  }
}

export async function getSavedGrants(): Promise<string[]> {
  const { data } = await api.get('/profile/saved-grants');
  if (!data || !Array.isArray(data.saved_grants)) {
    throw new Error("Invalid response format from getSavedGrants");
  }
  return data.saved_grants as string[];
}

export async function saveGrant(grantId: string): Promise<void> {
  await api.post('/profile/saved-grants', { grant_id: grantId });
}

export async function removeSavedGrant(grantId: string): Promise<void> {
  await api.del(`/profile/saved-grants/${grantId}`);
}

// Applications API
const applicationStatusMap: Record<string, Application["status"]> = {
  draft: 'draft',
  submitted: 'submitted',
  approved: 'approved',
  rejected: 'rejected',
};

export async function getApplications(): Promise<Application[]> {
  const { data } = await api.get('/applications');
  if (!data || !Array.isArray(data)) {
    throw new Error("Invalid response format from getApplications");
  }
  return data.map(mapApplicationFromBackend);
}

export async function getApplication(
  id: string,
): Promise<Application | undefined> {
  try {
    const { data } = await api.get(`/applications/${id}`);
    return mapApplicationFromBackend(data);
  } catch (error) {
    const status = (error as { status?: number }).status;
    if (status === 404 || status === 401) return undefined;
    throw error;
  }
}

export async function createApplication(
  application: { grantId: string; content?: string },
): Promise<Application> {
  const { data } = await api.post('/applications', {
    grant_id: application.grantId,
    content: application.content,
  });
  return mapApplicationFromBackend(data);
}

export async function updateApplication(
  id: string,
  updates: { content?: string; status?: 'draft' | 'submitted' },
): Promise<Application> {
  const { data } = await api.patch(`/applications/${id}`, {
    content: updates.content,
    status: updates.status,
  });
  return mapApplicationFromBackend(data);
}

export async function deleteApplication(id: string): Promise<void> {
  await api.del(`/applications/${id}`);
}

export function mapApplicationFromBackend(app: BackendApplication): Application {
  const status = applicationStatusMap[app.status as string] ?? 'draft';
  return {
    id: (app.id as string | number | undefined)?.toString() ?? '',
    grantId:
      (app.grant_id as string | number | undefined)?.toString() ||
      (app.grantId as string | undefined) ||
      '',
    grantTitle: (app.grant_name as string) || (app.grantTitle as string) || '',
    status,
    createdAt: app.created_at as string | undefined,
    updatedAt: app.updated_at as string | undefined,
    content: app.content as string | undefined,
  };
}

// Profile API
export function mapBackendProfileToFrontend(backendProfile: BackendProfile): Profile {
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
    selfDescription: backendProfile.selfDescription || backendProfile.self_description,
    legacyData: backendProfile.legacyData || backendProfile.legacy_data,
  };
}

export function mapFrontendProfileToBackend(profile: Profile): BackendProfile {
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
    selfDescription: profile.selfDescription,
    legacyData: profile.legacyData,
  };
}

export async function listProfiles(): Promise<Profile[]> {
  const { data } = await api.get('/profile/list');
  return data.map(mapBackendProfileToFrontend);
}

export async function getProfileById(id: number): Promise<Profile> {
  const { data } = await api.get(`/profile/${id}`);
  return mapBackendProfileToFrontend(data);
}

export async function createProfile(profile: Profile): Promise<Profile> {
  const { data } = await api.post('/profile/', mapBackendProfileToFrontend(profile));
  return mapBackendProfileToFrontend(data);
}

export async function updateProfileById(id: number, profile: Profile): Promise<Profile> {
  const { data } = await api.put(`/profile/${id}`, mapFrontendProfileToBackend(profile));
  return mapBackendProfileToFrontend(data);
}

export async function deleteProfile(id: number): Promise<void> {
  await api.del(`/profile/${id}`);
}

export async function getProfile(): Promise<Profile | null> {
  try {
    const { data } = await api.get('/profile/family');
    return mapBackendProfileToFrontend(data);
  } catch (error) {
    const status = (error as { status?: number }).status;
    if (status === 401 || status === 404) return null;
    throw error;
  }
}

export async function saveProfile(
  profile: Profile,
): Promise<Profile> {
  const { data } = await api.put('/profile/family', mapBackendProfileToFrontend(profile));
  return mapBackendProfileToFrontend(data);
}

export async function generateApplicationWithAI(
  _grantId: string,
  additionalContext?: string,
): Promise<{ generated_text: string; credits_remaining: number | null }> {
  // Backend endpoint: POST {base}/foundation-sync/generate-application
  // (GenerationRequest takes a prompt string; response: {response, model_used})
  const { data } = await api.post('/foundation-sync/generate-application', {
    prompt: additionalContext ?? '',
  });
  const result = data as { response?: string };
  return {
    generated_text: result.response ?? '',
    credits_remaining: null,
  };
}

export async function findMatchingFoundations(
  needs: string,
  threshold: number = 0.3,
  limit: number = 20,
  _profileId?: number
): Promise<MatchedFoundation[]> {
  const { data } = await api.post('/foundations/matching', { needs, threshold, limit });
  return mapMatchedFoundations(data);
}

export async function findMatchingFoundationsByProfile(
  profileId?: number,
  useGeoFilter: boolean = true,
  threshold: number = 0.25,
  limit: number = 100,
  useDescription: boolean = false
): Promise<MatchedFoundation[]> {
  const { data } = await api.post('/foundations/matching-by-profile', {
    profile_id: profileId,
    use_geographic_filter: useGeoFilter,
    use_description: useDescription,
    threshold,
    limit,
  });
  return mapMatchedFoundations(data);
}

// Matched foundations are consumed with a snake_case foundation object (the raw
// backend shape) except `parsed_service_area`, which the frontend model exposes
// as camelCase `parsedServiceArea`. See packages/types MatchedFoundation.
type BackendMatchedFoundation = MatchedFoundation & {
  foundation: MatchedFoundation["foundation"] & {
    parsed_service_area?: ParsedServiceArea;
  };
};

export function mapMatchedFoundations(data: BackendMatchedFoundation[]): MatchedFoundation[] {
  return (data ?? []).map((match) => {
    const { parsed_service_area, ...rest } = match.foundation;
    return {
      ...match,
      foundation: {
        ...rest,
        ...(parsed_service_area ? { parsedServiceArea: parsed_service_area } : {}),
      },
    };
  });
}
