import request from './request'

export function getCompanies() {
  return request.get('/companies')
}

export function getCompany(id) {
  return request.get(`/companies/${id}`)
}

export function createCompany(formData) {
  return request.post('/companies', formData)
}

export function updateCompany(id, formData) {
  return request.put(`/companies/${id}`, formData)
}

export function deleteCompany(id) {
  return request.delete(`/companies/${id}`)
}
