import { useEffect, useMemo, useState } from 'react'
import type { PropsWithChildren } from 'react'

import { AuthContext } from '@/context/auth-context'
import { getSession, login as apiLogin, logout as apiLogout } from '@/lib/api'
import type { AuthContextValue } from '@/context/auth-context'
import type { PrivateProfile } from '@/types/api'

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<PrivateProfile | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const refreshSession = async () => {
    const session = await getSession()
    setUser(session.user)
  }

  useEffect(() => {
    let mounted = true
    const loadSession = async () => {
      try {
        const session = await getSession()
        if (mounted) {
          setUser(session.user)
        }
      } catch {
        if (mounted) {
          setUser(null)
        }
      } finally {
        if (mounted) {
          setIsLoading(false)
        }
      }
    }
    void loadSession()
    return () => {
      mounted = false
    }
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isLoading,
      refreshSession,
      login: async (payload) => {
        const response = await apiLogin(payload)
        setUser(response.user)
        return response
      },
      logout: async () => {
        await apiLogout()
        setUser(null)
      },
      setUser,
    }),
    [isLoading, user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
