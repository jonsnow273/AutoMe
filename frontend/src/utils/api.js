import axios from 'axios'

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('autome_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Handle expired/invalid token globally
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Only redirect to login if the 401 happens on an authenticated request, not on auth routes
    const isAuthRoute = error.config?.url?.includes('/auth/login') ||
                        error.config?.url?.includes('/auth/signup') ||
                        error.config?.url?.includes('/auth/reset-password')

    if (error.response?.status === 401 && !isAuthRoute) {
      localStorage.removeItem('autome_token')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api
