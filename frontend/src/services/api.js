import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const analyzeCompany = (url, companyName, email) =>
  api.post('/analyze', { url, company_name: companyName, ...(email && { email }) })

export const getActiveAnalyses = () =>
  api.get('/analyses/active')

export const getAnalyses = (skip = 0, limit = 20) =>
  api.get('/analyses', { params: { skip, limit } })

export const getAnalysis = (id) =>
  api.get(`/analyses/${id}`)

export const deleteAnalysis = (id) =>
  api.delete(`/analyses/${id}`)

export const resendEmail = (id) =>
  api.post(`/analyses/${id}/resend-email`)

export const compareAnalysis = (id) =>
  api.get(`/analyses/${id}/compare`)

export default api
