import request from './request'

export function getWorks(params = {}) {
  return request.get('/works', { params })
}

export function getWork(id) {
  return request.get(`/works/${id}`)
}

export function createWork(formData) {
  return request.post('/works', formData)
}

export function updateWork(id, formData) {
  return request.put(`/works/${id}`, formData)
}

export function deleteWork(id) {
  return request.delete(`/works/${id}`)
}

export function getWorkHistory(id) {
  return request.get(`/works/${id}/history`)
}
