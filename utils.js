/**
 * Utility functions for common operations
 */

const Utils = {
    /**
     * Format date to readable string
     */
    formatDate(dateString) {
        if (!dateString) return "No date";
        const date = new Date(dateString);
        return date.toLocaleDateString("en-US", {
            year: "numeric",
            month: "short",
            day: "numeric",
        });
    },

    /**
     * Get status badge color
     */
    getStatusColor(status) {
        const statusMap = {
            "To Do": "#FF6B6B",
            "In Progress": "#FFD93D",
            "Completed": "#6BCF7F",
            "On Hold": "#A0AEC0",
        };
        return statusMap[status] || "#999999";
    },

    /**
     * Get status badge HTML
     */
    getStatusBadge(status) {
        const color = this.getStatusColor(status);
        return `<span style="background: ${color}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px;">${status}</span>`;
    },

    /**
     * Validate email format
     */
    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    },

    /**
     * Truncate text to specified length
     */
    truncateText(text, maxLength = 100) {
        if (!text) return "";
        return text.length > maxLength ? text.substring(0, maxLength) + "..." : text;
    },

    /**
     * Show notification (toast)
     */
    showNotification(message, type = "info", duration = 3000) {
        const notificationId = `notification-${Date.now()}`;
        const notification = document.createElement("div");
        notification.id = notificationId;
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            background: ${type === "error" ? "#FF6B6B" : type === "success" ? "#6BCF7F" : "#3B82F6"};
            color: white;
            border-radius: 5px;
            z-index: 9999;
            animation: slideIn 0.3s ease-in-out;
        `;

        document.body.appendChild(notification);

        setTimeout(() => {
            notification.style.animation = "slideOut 0.3s ease-in-out";
            setTimeout(() => notification.remove(), 300);
        }, duration);
    },

    /**
     * Parse error messages from API responses
     */
    getErrorMessage(error) {
        if (error.message) return error.message;
        if (error.response?.data?.message) return error.response.data.message;
        return "An unexpected error occurred. Please try again.";
    },

    /**
     * Debounce function to limit function calls
     */
    debounce(func, delay) {
        let timeoutId;
        return function (...args) {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => func.apply(this, args), delay);
        };
    }
};
/**
 * Display error messages in the UI
 * @param {string} message - The error message to show
 */
function displayErrorUI(message) {
    console.error('❌ Error:', message);
    
    // Try to find error container
    let errorContainer = document.getElementById('error-container');
    
    // Create one if it doesn't exist
    if (!errorContainer) {
        errorContainer = document.createElement('div');
        errorContainer.id = 'error-container';
        errorContainer.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #FF6B6B;
            color: white;
            padding: 15px 20px;
            border-radius: 5px;
            z-index: 10000;
            max-width: 500px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        `;
        document.body.appendChild(errorContainer);
    }
    
    errorContainer.innerHTML = `<strong>Error:</strong> ${message}`;
    errorContainer.style.display = 'block';
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        errorContainer.style.display = 'none';
    }, 5000);
}

console.log('✅ utils.js loaded, displayErrorUI defined:', typeof displayErrorUI);
