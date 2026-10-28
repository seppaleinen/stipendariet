import { createTokenStorage } from '@stipendariet/api-client';

const adminTokenStorage = createTokenStorage('adminToken');

export function getAdminAuthToken(): string | null {
  return adminTokenStorage.get();
}

export function clearAdminAuthToken(): void {
  adminTokenStorage.clear();
}