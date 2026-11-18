// si-archivo integraciones.autenticacion=clerk
"use client";
import { useAuth } from '@clerk/nextjs';
import { useEffect } from 'react';
import { setupClerkTokenInjection } from '@/utils/ClerkToken';
export default function ClerkTokenSetup() {
  const { getToken } = useAuth();
  useEffect(() => setupClerkTokenInjection(getToken), [getToken]);
  return null;
}
