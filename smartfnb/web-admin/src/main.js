import { createApp } from 'vue'
import { createRouter, createWebHistory } from 'vue-router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import App from './App.vue'
import Login from './views/Login.vue'
import Dashboard from './views/Dashboard.vue'
import AgentChat from './views/AgentChat.vue'
import Ops from './views/Ops.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/dashboard' },
    { path: '/login', component: Login },
    { path: '/dashboard', component: Dashboard },
    { path: '/agent', component: AgentChat },
    { path: '/ops', component: Ops }
  ]
})

document.documentElement.classList.add('dark')  // R8: 暗色模式默认(可回退)
const app = createApp(App)
app.use(router)
app.use(ElementPlus)
app.mount('#app')
