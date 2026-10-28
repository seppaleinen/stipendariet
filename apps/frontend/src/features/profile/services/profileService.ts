// Thin service wrappers around @/lib/api profile endpoints.
// No business logic here — this exists purely so ProfileContext can depend on
// the feature module instead of reaching into lib/api directly.
export {
  listProfiles,
  getProfileById,
  createProfile,
  updateProfileById,
  deleteProfile,
} from "@/lib/api";