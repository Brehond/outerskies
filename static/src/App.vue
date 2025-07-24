<template>
  <div id="app" class="min-h-screen theme-bg-primary theme-text-primary">
    <!-- Navigation Header -->
    <header class="theme-bg-secondary p-4 shadow-lg">
      <div class="container mx-auto flex justify-between items-center">
        <!-- Logo/Brand -->
        <div class="flex items-center space-x-4">
          <h1 class="text-2xl font-bold text-accent">🌌 Outer Skies</h1>
          <nav class="hidden md:flex space-x-6">
            <router-link to="/" class="nav-item hover:text-accent transition-colors">
              Chart Generator
            </router-link>
            <router-link to="/themes" class="nav-item hover:text-accent transition-colors">
              Themes
            </router-link>
            <router-link to="/dashboard" class="nav-item hover:text-accent transition-colors">
              Dashboard
            </router-link>
          </nav>
        </div>
        
        <!-- Theme Switcher -->
        <ThemeSwitcher />
      </div>
    </header>

    <!-- Main Content -->
    <main class="container mx-auto py-8">
      <router-view />
    </main>

    <!-- Loading Overlay -->
    <div v-if="loading" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-secondary p-6 rounded-lg flex items-center space-x-4">
        <div class="spinner-border border-accent border-t-transparent rounded-full animate-spin"></div>
        <span class="text-accent">Loading...</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useThemeStore } from './stores/theme'
import ThemeSwitcher from './components/ThemeSwitcher.vue'

const loading = ref(false)
const themeStore = useThemeStore()

onMounted(() => {
  // Initialize theme
  themeStore.initializeTheme()
})
</script>

<style>
/* Global styles will be imported from style.css */
</style> 