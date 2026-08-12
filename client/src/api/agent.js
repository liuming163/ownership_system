import request from './request'

export function getAgents(companyId) {
  const params = companyId ? { company_id: companyId } : {}
  return request.get('/agents', { params })
}

export function getAgent(id) {
  return request.get(`/agents/${id}`)
}

export function createAgent(formData) {
  return request.post('/agents', formData)
}

export function updateAgentAuth(id, formData) {
  return request.put(`/agents/${id}/auth`, formData)
}

export function getAuthHistory(id) {
  return request.get(`/agents/${id}/auth/history`)
}

export function deleteAgent(id) {
  return request.delete(`/agents/${id}`)
}
