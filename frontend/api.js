/**
 * API Service - Handles all backend communication
 * Provides error handling, retry logic, and response validation
 */

class APIService {
    constructor(baseURL) {
        this.baseURL = baseURL;
        this.timeout = 10000; // 10 seconds
    }

    /**
     * Generic fetch wrapper with error handling
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

        try {
            const response = await fetch(url, finalOptions);

            if (!response.ok) {
                throw new Error(`HTTP Error: ${response.status} ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API Request Failed [${endpoint}]:`, error);
            throw error;
        }
    }

    /**
     * Health check endpoint
     */
    async checkHealth() {
        return this.request(CONFIG.ENDPOINTS.HEALTH);
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

// Initialize API service
const api = new APIService(CONFIG.API_BASE_URL);
