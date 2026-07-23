import { createRouter, createWebHistory } from 'vue-router'
import type { LocationQuery, RouteLocationNormalized } from 'vue-router'

export function resolveLegacyEditorNavigation(query: LocationQuery) {
  const presentationId = query.presentationId
  if (typeof presentationId !== 'string' || !/^[A-Za-z0-9_-]{1,128}$/.test(presentationId)) return true
  return { name: 'PresentationEditor', params: { presentationId } }
}

export const routes = [
  {
    path: '/',
    name: 'Outline',
    component: () => import('@/views/Outline/index.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/works',
    name: 'Works',
    component: () => import('@/views/Works/index.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/editor',
    name: 'Editor',
    component: () => import('@/views/Editor/index.vue'),
    meta: { requiresAuth: true },
    beforeEnter: (to: RouteLocationNormalized) => resolveLegacyEditorNavigation(to.query),
  },
  {
    path: '/editor/:presentationId',
    name: 'PresentationEditor',
    component: () => import('@/views/Editor/index.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/ppt',
    name: 'PPT',
    component: () => import('@/views/PPT/index.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/app/:id?',
    name: 'APP',
    component: () => import('@/views/APP/index.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/auth-failure',
    name: 'AuthFailure',
    component: () => import('@/views/AuthFailure/index.vue'),
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
