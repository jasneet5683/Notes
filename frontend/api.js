/**
 * API Service - Handles all backend communication
 * Provides error handling, retry logic, and response validation
 * Compatible with Python backend (Railway) and HTML frontend (GitHub)
 */

class APIService {
    constructor(baseURL) {
        this.baseURL = baseURL;
        this.timeout = 10000; // 10 seconds
        this.maxRetries = 3;
        this.retryDelay = 1000; // milliseconds
    }

    /**
     * Generic fetch wrapper with error handling and retry logic
     */
    async request(endpoint, options = {}) {
        const url = `${this.baseURL}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
            timeout: this.timeout,
        };

        const finalOptions = { ...defaultOptions, ...options };
        let lastError;

        // Retry logic for network failures
        for (let attempt = 0; attempt < this.maxRetries; attempt++) {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), this.timeout);

                const response = await fetch(url, {
                    ...finalOptions,
                    signal: controller.signal,
                });

                clearTimeout(timeoutId);

                if (!response.ok) {
                    throw new Error(`HTTP Error: ${response.status} ${response.statusText}`);
                }

                return await response.json();
            } catch (error) {
                lastError = error;
                console.warn(`API Request Attempt ${attempt + 1}/${this.maxRetries} Failed [${endpoint}]:`, error);

                // Don't retry on HTTP errors, only network errors
                if (error.message.includes('HTTP Error')) {
                    break;
                }

                // Wait before retrying
                if (attempt < this.maxRetries - 1) {
                    await this.delay(this.retryDelay * (attempt + 1));
                }
            }
        }

        console.error(`API Request Failed [${endpoint}]:`, lastError);
        throw lastError;
    }

    /**
     * Utility: Delay function for retry logic
     */
    delay(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    /**
     * Health check endpoint
     */
    async checkHealth() {
        try {
            return await this.request(CONFIG.ENDPOINTS.HEALTH);
        } catch (error) {
            console.error('Health check failed:', error);
            return { status: 'unavailable' };
        }
    }

    /**
     * Send chat message to AI agent
     */
    async sendChatMessage(userMessage) {
        return this.request(CONFIG.ENDPOINTS.CHAT, {
            method: "POST",
            body: JSON.stringify({ user_message: userMessage }),
        });
    }

    /**
     * Fetch all tasks
     */
    async getTasks() {
        return this.request(CONFIG.ENDPOINTS.TASKS);
    }

    /**
     * Create a new task
     */
    async createTask(taskData) {
        return this.request(CONFIG.ENDPOINTS.TASKS, {
            method: "POST",
            body: JSON.stringify(taskData),
        });
    }

    /**
     * Update an existing task
     */
    async updateTask(taskId, taskData) {
        return this.request(`${CONFIG.ENDPOINTS.TASKS}/${taskId}`, {
            method: "PUT",
            body: JSON.stringify(taskData),
        });
    }

    /**
     * Delete a task
     */
    async deleteTask(taskId) {
        return this.request(`${CONFIG.ENDPOINTS.TASKS}/${taskId}`, {
            method: "DELETE",
        });
    }

    /**
     * Get AI-generated project summary
     */
    async getProjectSummary() {
        return this.request(CONFIG.ENDPOINTS.SUMMARY);
    }
}

// ✅ Initialization Guard: Ensure CONFIG exists before creating API instance
if (typeof CONFIG === 'undefined') {
    console.error('❌ CONFIG is not defined. Ensure config.js is loaded BEFORE api.js');
    throw new Error('CONFIG must be defined before APIService initialization');
}

const api = new APIService(CONFIG.API_BASE_URL);
console.log('✅ API Service initialized successfully');
