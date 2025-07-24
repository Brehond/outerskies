import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { createRouter, createWebHistory } from 'vue-router'
import App from './App.vue'
import './style.css'

// Import components
import ChartGenerator from './components/ChartGenerator.vue'
import ChartDisplay from './components/ChartDisplay.vue'
import Dashboard from './components/Dashboard.vue'
import ThemeSwitcher from './components/ThemeSwitcher.vue'

// Create router
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: ChartGenerator },
    { path: '/chart/:id', component: ChartDisplay },
    { path: '/dashboard', component: Dashboard },
    { path: '/themes', component: ThemeSwitcher }
  ]
})

// Create Pinia store
const pinia = createPinia()

// Create and mount app
const app = createApp(App)
app.use(pinia)
app.use(router)
app.mount('#app') 