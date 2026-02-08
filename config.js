// Configuration file for API endpoints and settings
const CONFIG = {
    // Update this URL with your Railway deployment URL
    API_BASE_URL: process.env.REACT_APP_API_URL || "https://notes-production-7134.up.railway.api",

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

// Export for use in other files
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CONFIG;
}
// Export for use in other files
window.CONFIG = CONFIG; // Make globally available in browser
