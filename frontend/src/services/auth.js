import api from './api'

const TOKEN_KEY = 'ca_token'
const USER_KEY = 'ca_user'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function getUser() {
  const raw = localStorage.getItem(USER_KEY)
  if (!raw) return null
  try {
    return JSON.parse(raw)
  } catch {
    return null
  }
}

export function isAuthenticated() {
  return !!getToken()
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

// Google Identity Services (GSI) — credential은 frontend GSI 버튼 콜백에서 전달됨
export async function verifyGoogleCredential(credential) {
  const { data } = await api.post('/auth/google/verify', { credential })
  localStorage.setItem(TOKEN_KEY, data.access_token)
  localStorage.setItem(
    USER_KEY,
    JSON.stringify({
      email: data.email,
      name: data.name,
      picture: data.picture,
      role: data.role,
      auth: 'google',
    })
  )
  return data
}

export async function fetchGoogleClientId() {
  try {
    const { data } = await api.get('/auth/google/config')
    return data?.client_id || ''
  } catch {
    return ''
  }
}

export async function fetchMe() {
  const { data } = await api.get('/auth/me')
  localStorage.setItem(USER_KEY, JSON.stringify(data))
  return data
}

// Inject Authorization header on every request
api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 401 → 자동 로그아웃
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err?.response?.status === 401) {
      logout()
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }
    return Promise.reject(err)
  }
)
