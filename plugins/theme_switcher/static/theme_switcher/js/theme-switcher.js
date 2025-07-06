// Theme Switcher JavaScript
class ThemeSwitcher {
    constructor() {
        this.currentTheme = null;
        this.themes = {
            'cosmic_night': {
                name: 'Cosmic Night',
                description: 'Deep space theme with purple and gold accents',
                colors: {
                    'primary': '#0a0a0f',
                    'secondary': '#1a1a2e',
                    'accent': '#ffd700',
                    'accent-secondary': '#ffed4e',
                    'text-primary': '#ffffff',
                    'text-secondary': '#e0e0e0',
                    'text-muted': '#a0a0a0',
                    'border': '#2a2a3e',
                    'border-light': '#3a3a4e',
                    'success': '#4ade80',
                    'error': '#f87171',
                    'warning': '#fbbf24',
                    'info': '#60a5fa'
                }
            },
            'sunset_orange': {
                name: 'Sunset Orange',
                description: 'Warm sunset theme with orange and red tones',
                colors: {
                    'primary': '#1a0f0f',
                    'secondary': '#2d1b1b',
                    'accent': '#ff6b35',
                    'accent-secondary': '#ff8c42',
                    'text-primary': '#ffffff',
                    'text-secondary': '#f0f0f0',
                    'text-muted': '#c0c0c0',
                    'border': '#3d2b2b',
                    'border-light': '#4d3b3b',
                    'success': '#4ade80',
                    'error': '#f87171',
                    'warning': '#fbbf24',
                    'info': '#60a5fa'
                }
            },
            'ocean_deep': {
                name: 'Ocean Deep',
                description: 'Deep ocean theme with blue and teal accents',
                colors: {
                    'primary': '#0a1a2a',
                    'secondary': '#1a2a3a',
                    'accent': '#00d4aa',
                    'accent-secondary': '#00f5d4',
                    'text-primary': '#ffffff',
                    'text-secondary': '#e0f0ff',
                    'text-muted': '#a0b0c0',
                    'border': '#2a3a4a',
                    'border-light': '#3a4a5a',
                    'success': '#4ade80',
                    'error': '#f87171',
                    'warning': '#fbbf24',
                    'info': '#60a5fa'
                }
            },
            'forest_green': {
                name: 'Forest Green',
                description: 'Natural forest theme with green and brown tones',
                colors: {
                    'primary': '#0a1a0a',
                    'secondary': '#1a2a1a',
                    'accent': '#4ade80',
                    'accent-secondary': '#22c55e',
                    'text-primary': '#ffffff',
                    'text-secondary': '#e0ffe0',
                    'text-muted': '#a0c0a0',
                    'border': '#2a3a2a',
                    'border-light': '#3a4a3a',
                    'success': '#4ade80',
                    'error': '#f87171',
                    'warning': '#fbbf24',
                    'info': '#60a5fa'
                }
            },
            'rose_gold': {
                name: 'Rose Gold',
                description: 'Elegant rose gold theme with pink and gold accents',
                colors: {
                    'primary': '#1a0f1a',
                    'secondary': '#2a1f2a',
                    'accent': '#f4a261',
                    'accent-secondary': '#e76f51',
                    'text-primary': '#ffffff',
                    'text-secondary': '#f0e0f0',
                    'text-muted': '#c0a0c0',
                    'border': '#3a2f3a',
                    'border-light': '#4a3f4a',
                    'success': '#4ade80',
                    'error': '#f87171',
                    'warning': '#fbbf24',
                    'info': '#60a5fa'
                }
            },
            'midnight_purple': {
                name: 'Midnight Purple',
                description: 'Deep purple theme with mystical vibes',
                colors: {
                    'primary': '#0a0a1a',
                    'secondary': '#1a1a2a',
                    'accent': '#a855f7',
                    'accent-secondary': '#c084fc',
                    'text-primary': '#ffffff',
                    'text-secondary': '#e0e0ff',
                    'text-muted': '#a0a0c0',
                    'border': '#2a2a3a',
                    'border-light': '#3a3a4a',
                    'success': '#4ade80',
                    'error': '#f87171',
                    'warning': '#fbbf24',
                    'info': '#60a5fa'
                }
            },
            'classic_dark': {
                name: 'Classic Dark',
                description: 'Traditional dark theme with gray tones',
                colors: {
                    'primary': '#0a0a0a',
                    'secondary': '#1a1a1a',
                    'accent': '#3b82f6',
                    'accent-secondary': '#60a5fa',
                    'text-primary': '#ffffff',
                    'text-secondary': '#e5e5e5',
                    'text-muted': '#a0a0a0',
                    'border': '#2a2a2a',
                    'border-light': '#3a3a3a',
                    'success': '#4ade80',
                    'error': '#f87171',
                    'warning': '#fbbf24',
                    'info': '#60a5fa'
                }
            },
            'light_mode': {
                name: 'Light Mode',
                description: 'Clean light theme for daytime use',
                colors: {
                    'primary': '#ffffff',
                    'secondary': '#f8f9fa',
                    'accent': '#3b82f6',
                    'accent-secondary': '#1d4ed8',
                    'text-primary': '#1f2937',
                    'text-secondary': '#374151',
                    'text-muted': '#6b7280',
                    'border': '#e5e7eb',
                    'border-light': '#f3f4f6',
                    'success': '#059669',
                    'error': '#dc2626',
                    'warning': '#d97706',
                    'info': '#2563eb'
                }
            }
        };
        
        this.init();
    }
    
    init() {
        // Load current theme from session/localStorage
        this.loadCurrentTheme();
        
        // Apply theme immediately
        this.applyTheme(this.currentTheme);
        
        // Initialize theme dropdown if it exists
        this.initThemeDropdown();
        
        // Listen for theme change events
        this.listenForThemeChanges();
    }
    
    loadCurrentTheme() {
        // Try to get theme from session storage first
        this.currentTheme = sessionStorage.getItem('user_theme') || 'cosmic_night';
        
        // Validate theme exists
        if (!this.themes[this.currentTheme]) {
            this.currentTheme = 'cosmic_night';
        }
    }
    
    applyTheme(themeName) {
        const theme = this.themes[themeName];
        if (!theme) {
            console.error('Theme not found:', themeName);
            return;
        }
        
        const root = document.documentElement;
        
        // Apply CSS custom properties
        Object.entries(theme.colors).forEach(([key, value]) => {
            const cssVar = `--${key.replace('_', '-')}-color`;
            root.style.setProperty(cssVar, value);
        });
        
        // Update body classes
        document.body.className = document.body.className.replace(/theme-\w+/g, '');
        document.body.classList.add(`theme-${themeName}`);
        
        // Store in session storage
        sessionStorage.setItem('user_theme', themeName);
        
        // Update current theme
        this.currentTheme = themeName;
        
        // Dispatch custom event
        document.dispatchEvent(new CustomEvent('themeChanged', {
            detail: { theme: themeName, themeData: theme }
        }));
        
        console.log(`Theme applied: ${theme.name}`);
    }
    
    switchTheme(themeName) {
        if (!this.themes[themeName]) {
            console.error('Invalid theme:', themeName);
            return Promise.reject(new Error('Invalid theme'));
        }
        
        const csrfToken = this.getCSRFToken();
        if (!csrfToken) {
            console.error('CSRF token not found, cannot switch theme');
            return Promise.reject(new Error('Security token not found. Please refresh the page and try again.'));
        }
        
        return fetch('/theme/switch/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({ theme: themeName })
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                this.applyTheme(themeName);
                return data;
            } else {
                throw new Error(data.error || 'Failed to switch theme');
            }
        });
    }
    
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        if (!token) {
            console.warn('CSRF token not found in the page');
            return '';
        }
        return token.value;
    }
    
    initThemeDropdown() {
        const dropdown = document.getElementById('theme-dropdown');
        if (!dropdown) {
            console.log('Theme dropdown not found, skipping initialization');
            return;
        }
        
        // Check if dropdown content already exists
        const existingContent = dropdown.querySelector('.theme-dropdown-content');
        if (existingContent) {
            console.log('Theme dropdown content already exists, skipping initialization');
            return;
        }
        
        // Create dropdown content
        const content = document.createElement('div');
        content.className = 'theme-dropdown-content';
        
        Object.entries(this.themes).forEach(([key, theme]) => {
            const option = document.createElement('div');
            option.className = `theme-option ${key === this.currentTheme ? 'active' : ''}`;
            option.innerHTML = `
                <div class="theme-color-preview" style="background: ${theme.colors.accent}"></div>
                <div>
                    <div style="color: var(--text-primary-color); font-weight: 600;">${theme.name}</div>
                    <div style="color: var(--text-secondary-color); font-size: 0.8em;">${theme.description}</div>
                </div>
            `;
            
            option.addEventListener('click', () => {
                this.switchTheme(key);
            });
            
            content.appendChild(option);
        });
        
        dropdown.appendChild(content);
    }
    
    listenForThemeChanges() {
        // Listen for theme change events from other parts of the app
        document.addEventListener('themeChanged', (event) => {
            console.log('Theme changed event received:', event.detail);
        });
    }
    
    // Public methods for external use
    getCurrentTheme() {
        return this.currentTheme;
    }
    
    getThemeData(themeName = null) {
        const theme = themeName || this.currentTheme;
        return this.themes[theme];
    }
    
    getAllThemes() {
        return this.themes;
    }
    
    // Utility method to create theme preview
    createThemePreview(themeName) {
        const theme = this.themes[themeName];
        if (!theme) return null;
        
        return {
            name: theme.name,
            description: theme.description,
            colors: theme.colors,
            preview: {
                primary: theme.colors.primary,
                secondary: theme.colors.secondary,
                accent: theme.colors.accent
            }
        };
    }
}

// Initialize theme switcher when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if the theme dropdown exists (for dropdown pages)
    const dropdown = document.getElementById('theme-dropdown');
    if (dropdown) {
        window.themeSwitcher = new ThemeSwitcher();
    }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ThemeSwitcher;
} 