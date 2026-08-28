export function getAdminAuthToken(): string | null {
  return localStorage.getItem('adminToken');
}
