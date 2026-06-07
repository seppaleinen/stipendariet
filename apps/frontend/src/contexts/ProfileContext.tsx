import React, { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { Profile, listProfiles, getProfileById, createProfile as apiCreateProfile, updateProfileById } from "@/lib/api";
import { useAuth } from "./AuthContext";

interface ProfileContextType {
  profiles: Profile[];
  activeProfile: Profile | null;
  isLoading: boolean;
  setActiveProfile: (profile: Profile) => void;
  refreshProfiles: () => Promise<void>;
  createProfile: (data: Profile) => Promise<Profile>;
  updateProfile: (id: number, data: Profile) => Promise<Profile>;
}

const ProfileContext = createContext<ProfileContextType | undefined>(undefined);

export function ProfileProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated, user } = useAuth();
  const [profiles, setProfiles] = useState<Profile[]>([]);
  const [activeProfile, setActiveProfileState] = useState<Profile | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Load profiles when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      refreshProfiles();
    } else {
      setProfiles([]);
      setActiveProfileState(null);
    }
  }, [isAuthenticated]);

  const refreshProfiles = async () => {
    setIsLoading(true);
    try {
      const data = await listProfiles();
      setProfiles(data);

      // Restore active profile from local storage or set default
      const savedProfileId = localStorage.getItem("activeProfileId");
      let selectedProfile = null;

      if (savedProfileId) {
        selectedProfile = data.find(p => p.id === parseInt(savedProfileId)) || null;
      }

      if (!selectedProfile && data.length > 0) {
        // Fallback to default or first
        selectedProfile = data.find(p => p.isDefault) || data[0];
      }

      // If we found a profile, set it as active
      if (selectedProfile) {
        setActiveProfileState(selectedProfile);
        if (selectedProfile.id) {
          localStorage.setItem("activeProfileId", String(selectedProfile.id));
        }
      } else {
        setActiveProfileState(null);
        localStorage.removeItem("activeProfileId");
      }

    } catch (error) {
      console.error("Failed to load profiles:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const setActiveProfile = (profile: Profile) => {
    setActiveProfileState(profile);
    if (profile.id) {
      localStorage.setItem("activeProfileId", String(profile.id));
    }
  };

  const createProfile = async (data: Profile): Promise<Profile> => {
    try {
      const newProfile = await apiCreateProfile(data);
      await refreshProfiles(); // Refresh list
      
      // If no active profile, or if this is the first one, set it active
       // (API logic handles default flag, refreshProfiles handles selection logic)
       
      // Force set active if it's the only one (handled by refreshProfiles technically but good to be explicit if needed)
      // Actually, refreshProfiles logic above will select it if it's the first/default.
      
      return newProfile;
    } catch (error) {
      throw error;
    }
  };

  const updateProfile = async (id: number, data: Profile): Promise<Profile> => {
    try {
      const updated = await updateProfileById(id, data);
      
      // Update local state without full refresh if possible, but full refresh ensures consistency
      await refreshProfiles();
      return updated;
    } catch (error) {
      throw error;
    }
  };

  return (
    <ProfileContext.Provider 
      value={{ 
        profiles, 
        activeProfile, 
        isLoading, 
        setActiveProfile, 
        refreshProfiles,
        createProfile,
        updateProfile
      }}
    >
      {children}
    </ProfileContext.Provider>
  );
}

export function useProfile() {
  const context = useContext(ProfileContext);
  if (context === undefined) {
    throw new Error("useProfile must be used within a ProfileProvider");
  }
  return context;
}
