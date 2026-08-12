import request from './request'

export function login(username, password) {
  return request.post('/login', { username, password })
}

export function logout() {
  return request.post('/logout')
}

export function getUserInfo() {
  return request.get('/user/info')
}
