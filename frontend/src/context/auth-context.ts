import { createContext } from 'react'

import type { AuthResponse, LoginMethod, PrivateProfile } from '@/types/api'

export interface AuthContextValue {
  user: PrivateProfile | null
  isAuthenticated: boolean
  isLoading: boolean
  refreshSession: () => Promise<void>
  login: (payload: {
    login_method: LoginMethod
    identifier: string
    password: string
  }) => Promise<AuthResponse>
  logout: () => Promise<void>
  setUser: (user: PrivateProfile | null) => void
}

export const AuthContext = createContext<AuthContextValue | null>(null)
