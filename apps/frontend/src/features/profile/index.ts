// Feature-local types
export type { ProfileSetupFormValues, ProfileService } from "./types";
export { profileSetupSchema } from "./types";

// Service wrappers (the DI seam)
export {
  listProfiles,
  createProfile,
  updateProfileById,
  getProfileById,
  deleteProfile,
} from "./services/profileService";

// Components
export { ProfileSetupForm } from "./components/ProfileSetupForm";
export { ProfileSwitcher } from "./components/ProfileSwitcher";