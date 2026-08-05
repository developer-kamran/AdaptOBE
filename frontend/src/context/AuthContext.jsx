import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { login as loginRequest } from '../api/auth'
import { apiFetch, clearTokens, getAccessToken, setTokens } from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  // Distinguishes "still checking for a saved session" from "checked, no session" -
  // without it, routes would flash a login screen on every page refresh.
  const [isLoading, setIsLoading] = useState(true)

  const loadCurrentUser = useCallback(async () => {
    try {
      const currentUser = await apiFetch('/api/v1/auth/me')
      setUser(currentUser)
    } catch {
      clearTokens()
      setUser(null)
    }
  }, [])

  useEffect(() => {
    ;(async () => {
      if (getAccessToken()) {
        await loadCurrentUser()
      }
      setIsLoading(false)
    })()
  }, [loadCurrentUser])

  const login = useCallback(
    async (email, password) => {
      const tokens = await loginRequest(email, password)
      setTokens(tokens)
      await loadCurrentUser()
    },
    [loadCurrentUser],
  )

  const logout = useCallback(() => {
    clearTokens()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
