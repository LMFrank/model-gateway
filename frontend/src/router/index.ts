import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

export type NavIconKey = 'Monitor' | 'SetUp' | 'Collection' | 'Share' | 'TrendCharts'

export interface AppRouteMeta {
  title: string
  nav: boolean
  icon?: NavIconKey
}

export const appRoutes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: '概览', nav: true, icon: 'Monitor' },
  },
  {
    path: '/providers',
    name: 'Providers',
    component: () => import('@/views/Providers.vue'),
    meta: { title: 'Provider 管理', nav: true, icon: 'SetUp' },
  },
  {
    path: '/models',
    name: 'Models',
    component: () => import('@/views/Models.vue'),
    meta: { title: '模型管理', nav: true, icon: 'Collection' },
  },
  {
    path: '/routes',
    name: 'Routes',
    component: () => import('@/views/Routes.vue'),
    meta: { title: '路由规则', nav: true, icon: 'Share' },
  },
  {
    path: '/usage',
    name: 'Usage',
    component: () => import('@/views/Usage.vue'),
    meta: { title: '使用量统计', nav: true, icon: 'TrendCharts' },
  },
]

export const navigationRoutes = appRoutes.filter(
  (route): route is RouteRecordRaw & { meta: AppRouteMeta } =>
    Boolean((route.meta as AppRouteMeta | undefined)?.nav),
)

const router = createRouter({
  history: createWebHistory(),
  routes: appRoutes,
})

export default router
