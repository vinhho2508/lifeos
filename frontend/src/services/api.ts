import axios from 'axios'

/** Drop the stale token and send the user to the login page. */
export function handleUnauthorized(): void {
  localStorage.removeItem('token')
  if (window.location.pathname !== '/login') {
    window.location.replace('/login')
  }
}

const api = axios.create({
  baseURL: '/api',
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Login itself returns 401 for a bad Google token; let the page show that error.
    if (error?.response?.status === 401 && error.config?.url !== '/auth/login') {
      handleUnauthorized()
    }
    return Promise.reject(error)
  },
)

export default api
