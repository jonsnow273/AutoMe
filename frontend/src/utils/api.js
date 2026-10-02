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
    if (error.response?.status === 401) {
      localStorage.removeItem('autome_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api
