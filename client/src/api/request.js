import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
  withCredentials: true,
})

request.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    const data = error.response?.data
    if (error.response?.status === 401 || data?.login_required) {
      router.push({ name: 'Login', query: { redirect: router.currentRoute.value.fullPath } })
      return Promise.reject(error)
    }
    const msg = data?.error || '请求失败'
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

export default request
