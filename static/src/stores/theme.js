import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import axios from 'axios'

export const useThemeStore = defineStore('theme', () => {
  const currentTheme = ref('cosmic-night')
  const themes = ref([])
  const loading = ref(false)

  // Computed properties
  const currentThemeData = computed(() => {
    return themes.value.find(theme => theme.slug === currentTheme.value)
  })

  // Actions
  const initializeTheme = async () => {
    try {
      loading.value = true
      const response = await axios.get('/api/themes/')
      themes.value = response.data.themes
      
      // Get saved theme from localStorage or default
      const savedTheme = localStorage.getItem('outer-skies-theme')
      if (savedTheme && themes.value.find(t => t.slug === savedTheme)) {
        currentTheme.value = savedTheme
      }
      
      applyTheme(currentTheme.value)
    } catch (error) {
      console.error('Failed to load themes:', error)
    } finally {
      loading.value = false
    }
  }

  const switchTheme = async (themeSlug) => {
    try {
      loading.value = true
      
      const response = await axios.post('/theme/switch/', {
        theme: themeSlug
      }, {
        headers: {
          'X-CSRFToken': getCSRFToken()
        }
      })

      if (response.data.success) {
        currentTheme.value = themeSlug
        localStorage.setItem('outer-skies-theme', themeSlug)
        applyTheme(themeSlug)
      }
    } catch (error) {
      console.error('Failed to switch theme:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  const applyTheme = (themeSlug) => {
    const theme = themes.value.find(t => t.slug === themeSlug)
    if (!theme) return

    const root = document.documentElement
    const colors = theme.colors

    // Apply CSS custom properties
    Object.entries(colors).forEach(([key, value]) => {
      if (value) {
        root.style.setProperty(`--${key.replace('_', '-')}`, value)
      }
    })

    // Update body data attribute
    document.body.setAttribute('data-theme', themeSlug)
  }

  const getCSRFToken = () => {
    const token = document.querySelector('[name=csrfmiddlewaretoken]')
    return token ? token.value : null
  }

  return {
    currentTheme,
    themes,
    loading,
    currentThemeData,
    initializeTheme,
    switchTheme,
    applyTheme
  }
}) 