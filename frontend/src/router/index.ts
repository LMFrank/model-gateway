import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '@/views/Dashboard.vue'
import Providers from '@/views/Providers.vue'
import Models from '@/views/Models.vue'
import Routes from '@/views/Routes.vue'
import Usage from '@/views/Usage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'Dashboard', component: Dashboard },
    { path: '/providers', name: 'Providers', component: Providers },
    { path: '/models', name: 'Models', component: Models },
    { path: '/routes', name: 'Routes', component: Routes },
    { path: '/usage', name: 'Usage', component: Usage },
  ],
})

export default router
