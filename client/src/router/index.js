import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '../stores/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    component: () => import('../components/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: '/companies' },
      {
        path: 'companies',
        name: 'Companies',
        component: () => import('../views/CompanyView.vue'),
      },
      {
        path: 'agents',
        name: 'Agents',
        component: () => import('../views/AgentView.vue'),
      },
      {
        path: 'works',
        name: 'Works',
        component: () => import('../views/WorkView.vue'),
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const userStore = useUserStore()

  if (to.meta.requiresAuth !== false) {
    if (!userStore.username) {
      try {
        await userStore.fetchUser()
      } catch {
        return { name: 'Login', query: { redirect: to.fullPath } }
      }
    }
  }
})

export default router
