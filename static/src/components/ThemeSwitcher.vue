<template>
  <div class="theme-switcher relative">
    <button 
      @click="toggleDropdown"
      class="theme-dropdown-trigger flex items-center space-x-2 px-4 py-2 bg-primary border border-border rounded-lg hover:bg-secondary transition-colors"
    >
      <span>🎨</span>
      <span class="hidden sm:inline">Theme</span>
      <span class="transform transition-transform" :class="{ 'rotate-180': isOpen }">▼</span>
    </button>

    <div 
      v-if="isOpen"
      class="theme-dropdown-content absolute right-0 mt-2 w-64 bg-secondary border border-border rounded-lg shadow-lg z-50 max-h-96 overflow-y-auto"
    >
      <div class="p-2">
        <div 
          v-for="theme in themes" 
          :key="theme.slug"
          @click="selectTheme(theme.slug)"
          class="theme-option flex items-center space-x-3 p-3 rounded-lg cursor-pointer transition-colors hover:bg-primary"
          :class="{ 'bg-accent text-primary': currentTheme === theme.slug }"
        >
          <div 
            class="theme-color-preview w-6 h-6 rounded border-2 border-border"
            :style="{ backgroundColor: theme.colors.accent }"
          ></div>
          <span class="theme-name-text font-medium">{{ theme.name }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useThemeStore } from '../stores/theme'

const themeStore = useThemeStore()
const isOpen = ref(false)

// Computed properties
const currentTheme = computed(() => themeStore.currentTheme)
const themes = computed(() => themeStore.themes)

// Methods
const toggleDropdown = () => {
  isOpen.value = !isOpen.value
}

const selectTheme = async (themeSlug) => {
  try {
    await themeStore.switchTheme(themeSlug)
    isOpen.value = false
  } catch (error) {
    console.error('Failed to switch theme:', error)
  }
}

// Close dropdown when clicking outside
const handleClickOutside = (event) => {
  if (!event.target.closest('.theme-switcher')) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.theme-dropdown-content {
  scrollbar-width: thin;
  scrollbar-color: var(--border-color) var(--secondary-color);
}

.theme-dropdown-content::-webkit-scrollbar {
  width: 6px;
}

.theme-dropdown-content::-webkit-scrollbar-track {
  background: var(--secondary-color);
}

.theme-dropdown-content::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: 3px;
}
</style> 