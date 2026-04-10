import axios, { AxiosHeaders } from 'axios'

const buildAdminToken = import.meta.env.VITE_GATEWAY_ADMIN_TOKEN?.trim()
const ADMIN_TOKEN_STORAGE_KEY = 'mgw_admin_token'

const isProtectedUrl = (url: string) => url.startsWith('/api') || url.startsWith('/admin')

const getStoredAdminToken = () => {
  if (typeof window === 'undefined') return null
  return window.localStorage.getItem(ADMIN_TOKEN_STORAGE_KEY)?.trim() || null
}

const client = axios.create({
  baseURL: '',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

client.interceptors.request.use((config) => {
  const url = config.url ?? ''
  const adminToken = getStoredAdminToken() || buildAdminToken
  if (
    adminToken &&
    isProtectedUrl(url) &&
    !config.headers?.Authorization
  ) {
    const headers = AxiosHeaders.from(config.headers ?? {})
    headers.set('Authorization', `Bearer ${adminToken}`)
    config.headers = headers
  }
  return config
})

client.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error.response?.status
    const requestConfig = error.config as (typeof error.config & { _mgwRetried?: boolean }) | undefined
    const url = requestConfig?.url ?? ''

    if (
      status === 401 &&
      requestConfig &&
      isProtectedUrl(url) &&
      !requestConfig._mgwRetried &&
      !getStoredAdminToken() &&
      typeof window !== 'undefined'
    ) {
      const input = window.prompt('请输入 GATEWAY_ADMIN_TOKEN 以访问管理接口')
      const token = input?.trim()
      if (token) {
        window.localStorage.setItem(ADMIN_TOKEN_STORAGE_KEY, token)
        requestConfig._mgwRetried = true
        const headers = AxiosHeaders.from(requestConfig.headers ?? {})
        headers.set('Authorization', `Bearer ${token}`)
        requestConfig.headers = headers
        return client(requestConfig)
      }
    }

    return Promise.reject(error)
  },
)

export default client
