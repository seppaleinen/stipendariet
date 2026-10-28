import { describe, it, expect, vi } from "vitest";
import * as Api from "@/lib/api";
import * as profileService from "../services/profileService";

// Mock @/lib/api so the spies below are the exact references the service
// re-exports. Because the service module is a plain re-export, the exported
// bindings must be the same function objects as the ones on the Api module.
vi.mock("@/lib/api", () => ({
  listProfiles: vi.fn(),
  getProfileById: vi.fn(),
  createProfile: vi.fn(),
  updateProfileById: vi.fn(),
  deleteProfile: vi.fn(),
}));

describe("profileService", () => {
  it("re-exports listProfiles from @/lib/api (identity)", () => {
    expect(profileService.listProfiles).toBe(Api.listProfiles);
  });

  it("re-exports getProfileById from @/lib/api (identity)", () => {
    expect(profileService.getProfileById).toBe(Api.getProfileById);
  });

  it("re-exports createProfile from @/lib/api (identity)", () => {
    expect(profileService.createProfile).toBe(Api.createProfile);
  });

  it("re-exports updateProfileById from @/lib/api (identity)", () => {
    expect(profileService.updateProfileById).toBe(Api.updateProfileById);
  });

  it("re-exports deleteProfile from @/lib/api (identity)", () => {
    expect(profileService.deleteProfile).toBe(Api.deleteProfile);
  });
});