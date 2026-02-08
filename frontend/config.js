// Configuration file for API endpoints and settings
const CONFIG = {
    // Direct URL - no environment variables in browser
    API_BASE_URL: "https://notes-production-7134.up.railway.app",
    
    REFRESH_INTERVAL: 5000, // ms
    TIMEOUT: 10000, // ms
    
    // Feature flags
    FEATURES: {
        CHAT_ENABLED: true,
        TASK_MANAGEMENT: true,
        ANALYTICS: true
    },
    
    // UI settings
    UI: {
        CHAT_BOX_HEIGHT: 400,
        MAX_MESSAGE_LENGTH: 500,
        AUTO_REFRESH_INTERVAL: 30000 // 30 seconds
    },
    
    // API endpoints
    ENDPOINTS: {
        HEALTH: "/api/health",
        CHAT: "/api/chat",
        TASKS: "/api/tasks",
        SUMMARY: "/api/summary"
    }
};

// Make globally available for other scripts
window.CONFIG = CONFIG;
console.log('✅ CONFIG initialized:', CONFIG.API_BASE_URL);
