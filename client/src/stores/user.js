import { defineStore } from 'pinia'
import { getUserInfo, login, logout } from '../api/auth'

export const useUserStore = defineStore('user', {
  state: () => ({
    username: '',
    uid: null,
  }),

  getters: {
    canDelete() {
      return this.uid === 1717602
    },
  },

  actions: {
    async fetchUser() {
      const res = await getUserInfo()
      if (res.success) {
        this.username = res.data.username
        this.uid = res.data.uid ? Number(res.data.uid) : null
      } else {
        throw new Error(res.error || '未登录')
      }
    },

    async login(username, password) {
      const res = await login(username, password)
      if (res.success) {
        this.username = res.data.username
        this.uid = res.data.uid ? Number(res.data.uid) : null
      }
      return res
    },

    async logout() {
      await logout()
      this.username = ''
      this.uid = null
    },
  },
})
