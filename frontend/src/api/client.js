import axios from 'axios'

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

export const AUTH_STORAGE_KEYS = {
  access: 'kahvecell.accessToken',
  refresh: 'kahvecell.refreshToken',
  user: 'kahvecell.user',
}

export const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 12000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(AUTH_STORAGE_KEYS.access)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let refreshRequest

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const request = error.config
    const endpoint = request?.url || ''
    const isAuthRequest =
      endpoint.includes('/auth/register') ||
      endpoint.includes('/auth/verify-otp') ||
      endpoint.includes('/auth/refresh')

    if (error.response?.status !== 401 || !request || request._retry || isAuthRequest) {
      return Promise.reject(error)
    }

    const refreshToken = localStorage.getItem(AUTH_STORAGE_KEYS.refresh)
    if (!refreshToken) {
      return Promise.reject(error)
    }

    request._retry = true
    try {
      if (!refreshRequest) {
        refreshRequest = axios
          .post(`${API_BASE_URL}/auth/refresh`, { refresh_token: refreshToken })
          .finally(() => {
            refreshRequest = undefined
          })
      }

      const { data } = await refreshRequest
      const tokens = data.data
      localStorage.setItem(AUTH_STORAGE_KEYS.access, tokens.access_token)
      localStorage.setItem(AUTH_STORAGE_KEYS.refresh, tokens.refresh_token)
      request.headers = request.headers || {}
      request.headers.Authorization = `Bearer ${tokens.access_token}`
      return api(request)
    } catch (refreshError) {
      localStorage.removeItem(AUTH_STORAGE_KEYS.access)
      localStorage.removeItem(AUTH_STORAGE_KEYS.refresh)
      localStorage.removeItem(AUTH_STORAGE_KEYS.user)
      window.dispatchEvent(new Event('kahvecell:auth-expired'))
      return Promise.reject(refreshError)
    }
  },
)

export function getErrorMessage(error, fallback = 'Bir hata oluştu.') {
  return error.response?.data?.error?.message || error.message || fallback
}
