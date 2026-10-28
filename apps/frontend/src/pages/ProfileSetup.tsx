import { Helmet } from "react-helmet-async";
import { SITE_URL } from "@/lib/page-metadata";
import { ProfileSetupForm } from "@/features/profile";

/**
 * Route target for /profile-setup and /family-setup.
 *
 * The form body lives in features/profile (ProfileSetupForm); this page
 * shell only holds the SEO head and mounts the form.
 */
export default function ProfileSetup() {
  return (
    <>
      <Helmet>
        <title>Skapa Profil - StipendieAssistenten</title>
        <meta name="description" content="Skapa din personliga profil för personliga stipendieförslag." />
        <meta name="robots" content="noindex, nofollow" />
        <link rel="canonical" href={`${SITE_URL}/profile-setup`} />
      </Helmet>
      <ProfileSetupForm />
    </>
  );
}
