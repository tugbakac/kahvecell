import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { api, AUTH_STORAGE_KEYS } from '../api/client'

const AuthContext = createContext(null)

function readStoredUser() {
  try {
    const value = localStorage.getItem(AUTH_STORAGE_KEYS.user)
    return value ? JSON.parse(value) : null
  } catch {
    return null
  }
}

export function AuthProvider({ children }) {
  const [accessToken, setAccessToken] = useState(() =>
    localStorage.getItem(AUTH_STORAGE_KEYS.access),
  )
  const [user, setUser] = useState(readStoredUser)

  const saveUser = useCallback((nextUser) => {
    setUser(nextUser)
    localStorage.setItem(AUTH_STORAGE_KEYS.user, JSON.stringify(nextUser))
  }, [])

  const clearSession = useCallback(() => {
    localStorage.removeItem(AUTH_STORAGE_KEYS.access)
    localStorage.removeItem(AUTH_STORAGE_KEYS.refresh)
    localStorage.removeItem(AUTH_STORAGE_KEYS.user)
    setAccessToken(null)
    setUser(null)
  }, [])

  useEffect(() => {
    window.addEventListener('kahvecell:auth-expired', clearSession)
    return () => window.removeEventListener('kahvecell:auth-expired', clearSession)
  }, [clearSession])

  const requestOtp = useCallback(async (phoneNumber) => {
    const response = await api.post('/auth/register', { phone_number: phoneNumber })
    return response.data.data
  }, [])

  const verifyOtp = useCallback(
    async (phoneNumber, otp) => {
      const response = await api.post('/auth/verify-otp', {
        phone_number: phoneNumber,
        otp,
      })
      const data = response.data.data
      localStorage.setItem(AUTH_STORAGE_KEYS.access, data.access_token)
      localStorage.setItem(AUTH_STORAGE_KEYS.refresh, data.refresh_token)
      setAccessToken(data.access_token)
      saveUser(data.user)
      return data.user
    },
    [saveUser],
  )

  const logout = useCallback(() => clearSession(), [clearSession])

  const value = useMemo(
    () => ({
      accessToken,
      user,
      isAuthenticated: Boolean(accessToken && user),
      requestOtp,
      verifyOtp,
      saveUser,
      logout,
    }),
    [accessToken, user, requestOtp, verifyOtp, saveUser, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
