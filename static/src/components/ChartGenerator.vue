<template>
  <div class="chart-generator">
    <div class="text-center mb-8">
      <h1 class="text-4xl font-extrabold mb-4 text-accent drop-shadow">Outer Skies</h1>
      <h2 class="text-2xl text-accent font-semibold">Generate Your Astrological Chart</h2>
    </div>

    <!-- Form -->
    <form @submit.prevent="generateChart" class="space-y-6 bg-secondary rounded-xl shadow p-8 mb-10 border-l-8 border-accent">
      <!-- Error/Success Messages -->
      <div v-if="errorMessage" class="bg-error-color text-white p-4 rounded-lg">
        {{ errorMessage }}
      </div>
      <div v-if="successMessage" class="bg-success-color text-white p-4 rounded-lg">
        {{ successMessage }}
      </div>

      <!-- Basic Information -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <label for="date" class="block text-sm font-semibold text-accent mb-2">Birth Date</label>
          <input 
            v-model="formData.date" 
            type="date" 
            id="date"
            class="w-full rounded-md border border-primary bg-primary text-accent placeholder-text-muted shadow-sm focus:ring-2 focus:ring-accent focus:border-transparent"
            required
          >
        </div>

        <div>
          <label for="time" class="block text-sm font-semibold text-accent mb-2">Birth Time</label>
          <input 
            v-model="formData.time" 
            type="time" 
            id="time"
            class="w-full rounded-md border border-primary bg-primary text-accent placeholder-text-muted shadow-sm focus:ring-2 focus:ring-accent focus:border-transparent"
            required
          >
        </div>

        <div>
          <label for="latitude" class="block text-sm font-semibold text-accent mb-2">Latitude</label>
          <input 
            v-model.number="formData.latitude" 
            type="number" 
            id="latitude"
            step="0.000001"
            class="w-full rounded-md border border-primary bg-primary text-accent placeholder-text-muted shadow-sm focus:ring-2 focus:ring-accent focus:border-transparent"
            required
          >
        </div>

        <div>
          <label for="longitude" class="block text-sm font-semibold text-accent mb-2">Longitude</label>
          <input 
            v-model.number="formData.longitude" 
            type="number" 
            id="longitude"
            step="0.000001"
            class="w-full rounded-md border border-primary bg-primary text-accent placeholder-text-muted shadow-sm focus:ring-2 focus:ring-accent focus:border-transparent"
            required
          >
        </div>

        <div>
          <label for="location" class="block text-sm font-semibold text-accent mb-2">Location Name</label>
          <input 
            v-model="formData.location" 
            type="text" 
            id="location"
            placeholder="City, Country"
            class="w-full rounded-md border border-primary bg-primary text-accent placeholder-text-muted shadow-sm focus:ring-2 focus:ring-accent focus:border-transparent"
          >
        </div>

        <div>
          <label for="timezone" class="block text-sm font-semibold text-accent mb-2">Timezone</label>
          <select 
            v-model="formData.timezone" 
            id="timezone"
            class="w-full rounded-md border border-primary bg-primary text-accent shadow-sm focus:ring-2 focus:ring-accent focus:border-transparent"
            required
          >
            <option value="">Select timezone...</option>
            <optgroup v-for="group in timezoneGroups" :key="group.label" :label="group.label">
              <option v-for="tz in group.timezones" :key="tz.value" :value="tz.value">
                {{ tz.label }}
              </option>
            </optgroup>
          </select>
        </div>

        <div>
          <label for="zodiac_type" class="block text-sm font-semibold text-accent mb-2">Zodiac Type</label>
          <select 
            v-model="formData.zodiac_type" 
            id="zodiac_type"
            class="w-full rounded-md border border-primary bg-primary text-accent shadow-sm focus:ring-2 focus:ring-accent focus:border-transparent"
            required
          >
            <option value="tropical">Tropical</option>
            <option value="sidereal">Sidereal</option>
          </select>
        </div>

        <div>
          <label for="house_system" class="block text-sm font-semibold text-accent mb-2">House System</label>
          <select 
            v-model="formData.house_system" 
            id="house_system"
            class="w-full rounded-md border border-primary bg-primary text-accent shadow-sm focus:ring-2 focus:ring-accent focus:border-transparent"
            required
          >
            <option value="placidus">Placidus</option>
            <option value="whole_sign">Whole Sign</option>
          </select>
        </div>
      </div>

      <!-- AI Settings -->
      <div class="border-t border-primary pt-6">
        <h3 class="text-lg font-semibold text-accent mb-4">AI Interpretation Settings</h3>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label for="model_name" class="block text-sm font-semibold text-accent mb-2">AI Model</label>
            <select 
              v-model="formData.model_name" 
              id="model_name"
              class="w-full rounded-md border border-primary bg-primary text-accent shadow-sm focus:ring-2 focus:ring-accent focus:border-transparent"
              required
            >
              <option v-for="model in availableModels" :key="model.value" :value="model.value">
                {{ model.label }}
              </option>
            </select>
          </div>

          <div>
            <label for="temperature" class="block text-sm font-semibold text-accent mb-2">
              Creativity Level: {{ formData.temperature }}
            </label>
            <input 
              v-model.number="formData.temperature" 
              type="range" 
              id="temperature"
              min="0" 
              max="1" 
              step="0.1"
              class="w-full"
            >
            <div class="text-xs text-text-muted mt-1">
              Lower = More factual, Higher = More creative
            </div>
          </div>

          <div>
            <label for="max_tokens" class="block text-sm font-semibold text-accent mb-2">
              Response Length: {{ formData.max_tokens }}
            </label>
            <input 
              v-model.number="formData.max_tokens" 
              type="range" 
              id="max_tokens"
              min="500" 
              max="2000" 
              step="100"
              class="w-full"
            >
          </div>
        </div>
      </div>

      <!-- Submit Button -->
      <div class="flex justify-center pt-6">
        <button 
          type="submit" 
          :disabled="loading"
          class="px-8 py-3 bg-accent text-primary rounded-lg font-semibold hover:bg-accent-secondary transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
        >
          <div v-if="loading" class="spinner-border border-primary border-t-transparent rounded-full animate-spin w-5 h-5"></div>
          <span>{{ loading ? 'Generating Chart...' : 'Generate Chart' }}</span>
        </button>
      </div>
    </form>

    <!-- Results -->
    <div v-if="chartResult" class="bg-secondary rounded-xl shadow p-8">
      <h3 class="text-2xl font-bold mb-6 text-accent">Your Chart Results</h3>
      <div class="space-y-6">
        <!-- Chart Data -->
        <div class="bg-primary p-6 rounded-lg">
          <h4 class="text-lg font-semibold text-accent mb-4">Chart Data</h4>
          <pre class="text-sm text-text-secondary overflow-x-auto">{{ JSON.stringify(chartResult.chart_data, null, 2) }}</pre>
        </div>

        <!-- Interpretations -->
        <div v-if="chartResult.planet_interpretations" class="bg-primary p-6 rounded-lg">
          <h4 class="text-lg font-semibold text-accent mb-4">Planet Interpretations</h4>
          <div class="prose prose-invert max-w-none">
            <div v-html="chartResult.planet_interpretations"></div>
          </div>
        </div>

        <div v-if="chartResult.master_interpretation" class="bg-primary p-6 rounded-lg">
          <h4 class="text-lg font-semibold text-accent mb-4">Master Interpretation</h4>
          <div class="prose prose-invert max-w-none">
            <div v-html="chartResult.master_interpretation"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()

// Reactive data
const loading = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const chartResult = ref(null)

const formData = reactive({
  date: '',
  time: '',
  latitude: null,
  longitude: null,
  location: '',
  timezone: '',
  zodiac_type: 'tropical',
  house_system: 'placidus',
  model_name: 'gpt-4',
  temperature: 0.7,
  max_tokens: 1000
})

// Available models
const availableModels = [
  { value: 'gpt-4', label: 'GPT-4' },
  { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
  { value: 'claude-3-opus', label: 'Claude 3 Opus' },
  { value: 'claude-3-sonnet', label: 'Claude 3 Sonnet' },
  { value: 'mistral-medium', label: 'Mistral Medium' },
  { value: 'mistral-7b', label: 'Mistral 7B' }
]

// Timezone groups
const timezoneGroups = [
  {
    label: 'North America',
    timezones: [
      { value: 'America/New_York', label: 'Eastern Time (ET) - New York' },
      { value: 'America/Chicago', label: 'Central Time (CT) - Chicago' },
      { value: 'America/Denver', label: 'Mountain Time (MT) - Denver' },
      { value: 'America/Los_Angeles', label: 'Pacific Time (PT) - Los Angeles' },
      { value: 'America/Toronto', label: 'Eastern Time (ET) - Toronto' },
      { value: 'America/Vancouver', label: 'Pacific Time (PT) - Vancouver' }
    ]
  },
  {
    label: 'Europe',
    timezones: [
      { value: 'Europe/London', label: 'Greenwich Mean Time (GMT) - London' },
      { value: 'Europe/Paris', label: 'Central European Time (CET) - Paris' },
      { value: 'Europe/Berlin', label: 'Central European Time (CET) - Berlin' },
      { value: 'Europe/Rome', label: 'Central European Time (CET) - Rome' }
    ]
  }
  // Add more timezone groups as needed
]

// Methods
const generateChart = async () => {
  try {
    loading.value = true
    errorMessage.value = ''
    successMessage.value = ''
    chartResult.value = null

    const response = await axios.post('/chart/generate/', formData, {
      headers: {
        'X-CSRFToken': getCSRFToken()
      }
    })

    if (response.data.success) {
      chartResult.value = response.data
      successMessage.value = 'Chart generated successfully!'
    } else {
      errorMessage.value = response.data.error || 'Failed to generate chart'
    }
  } catch (error) {
    console.error('Chart generation error:', error)
    errorMessage.value = error.response?.data?.error || 'An error occurred while generating the chart'
  } finally {
    loading.value = false
  }
}

const getCSRFToken = () => {
  const token = document.querySelector('[name=csrfmiddlewaretoken]')
  return token ? token.value : null
}

// Initialize form with current date/time
onMounted(() => {
  const now = new Date()
  formData.date = now.toISOString().split('T')[0]
  formData.time = now.toTimeString().slice(0, 5)
})
</script>

<style scoped>
.spinner-border {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style> 