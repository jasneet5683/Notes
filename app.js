/**
 * Main Application File
 * Handles UI interactions and state management
 */

let isInitialized = false;
let autoRefreshInterval = null;

/**
 * Initialize application on page load
 */
//document.addEventListener('DOMContentLoaded', initializeApp);
async function initializeApp() {
    console.log('🚀 Initializing application...');
    
    try {
        // Validate prerequisites
        if (!window.CONFIG) {
            throw new Error('CONFIG not loaded. Ensure config.js is first.');
        }
        
        if (!window.api) {
            throw new Error('API Service not initialized. Check api.js instantiation.');
        }
        
        if (typeof displayErrorUI !== 'function') {
            throw new Error('displayErrorUI function not defined. Check utils.js.');
        }
        // Now safe to proceed with initialization
        console.log('✅ All dependencies loaded. Proceeding...');
        
        // Your initialization logic here
        // await api.fetchTasks();
        // etc.
    } catch (error) {
        console.error('❌ Initialization failed:', error.message);
        displayErrorUI(error.message);
    }
}
// Call only when DOM is ready
document.addEventListener('DOMContentLoaded', initializeApp);


/**
 * Update health status indicator
 */
async function updateHealthStatus() {
    const statusIndicator = document.getElementById("status-indicator");

    try {
        const data = await api.checkHealth();
        const isHealthy = data.status === "healthy";

        statusIndicator.textContent = isHealthy ? "🟢 Online" : "🔴 Offline";
        statusIndicator.className = isHealthy ? "status-online" : "status-offline";
    } catch (error) {
        statusIndicator.textContent = "🔴 Offline";
        statusIndicator.className = "status-offline";
        console.warn("Backend health check failed:", error);
    }
}

/**
 * Load and display all tasks
 */
async function loadTasks() {
    const tasksContainer = document.getElementById("tasks-container");

    try {
        tasksContainer.innerHTML = '<p style="text-align: center; color: #999;">⏳ Loading tasks...</p>';

        const data = await api.getTasks();
        const tasks = data.tasks || [];

        if (tasks.length === 0) {
            tasksContainer.innerHTML = '<p style="text-align: center; color: #999;">No tasks found. Create one to get started!</p>';
            return;
        }

        tasksContainer.innerHTML = tasks.map(task => renderTaskCard(task)).join("");
    } catch (error) {
        console.error("Failed to load tasks:", error);
        tasksContainer.innerHTML = `<p style="color: red;">❌ Error loading tasks: ${Utils.getErrorMessage(error)}</p>`;
    }
}

/**
 * Render a single task card
 */
function renderTaskCard(task) {
    return `
        <div class="task-card" data-task-id="${task.id || task.TaskName}">
            <div class="task-header">
                <h3>${task.TaskName || "Unnamed Task"}</h3>
                ${Utils.getStatusBadge(task.Status)}
            </div>
            <div class="task-details">
                <p><strong>Assigned to:</strong> ${task.AssignedTo || "Unassigned"}</p>
                <p><strong>Client:</strong> ${task.Client || "N/A"}</p>
                <p><strong>Duration:</strong> ${Utils.formatDate(task.StartDate)} → ${Utils.formatDate(task.EndDate)}</p>
            </div>
            <div class="task-actions">
                <button onclick="editTask('${task.TaskName}')" class="btn-secondary">✏️ Edit</button>
                <button onclick="deleteTask('${task.TaskName}')" class="btn-danger">🗑️ Delete</button>
            </div>
        </div>
    `;
}

/**
 * Send message to AI chat agent
 */
async function sendMessage() {
    const userInput = document.getElementById("user-input");
    const userMessage = userInput.value.trim();

    if (!userMessage) {
        Utils.showNotification("⚠️ Please enter a message", "info");
        return;
    }

    if (userMessage.length > CONFIG.UI.MAX_MESSAGE_LENGTH) {
        Utils.showNotification(`⚠️ Message too long (max ${CONFIG.UI.MAX_MESSAGE_LENGTH} characters)`, "error");
        return;
    }

    const chatBox = document.getElementById("chat-box");

    // Display user message
    chatBox.appendChild(createMessageElement(userMessage, "user"));
    userInput.value = "";
    chatBox.scrollTop = chatBox.scrollHeight;

    // Show loading indicator
    const loadingEl = createMessageElement("🔄 Thinking...", "ai");
    chatBox.appendChild(loadingEl);
    chatBox.scrollTop = chatBox.scrollHeight;

    try {
        const data = await api.sendChatMessage(userMessage);
        loadingEl.remove();

        // Display AI response
        const aiResponse = data.response || "No response received";
        chatBox.appendChild(createMessageElement(aiResponse, "ai"));
        chatBox.scrollTop = chatBox.scrollHeight;
    } catch (error) {
        loadingEl.remove();
        const errorMessage = `❌ Error: ${Utils.getErrorMessage(error)}`;
        chatBox.appendChild(createMessageElement(errorMessage, "ai"));
        console.error("Chat error:", error);
    }
}

/**
 * Create message element for chat display
 */
function createMessageElement(text, sender) {
    const messageDiv = document.createElement("div");
    messageDiv.className = `message ${sender}-message`;
    messageDiv.innerHTML = `
        <div class="message-content">${escapeHTML(text)}</div>
        <span class="message-time">${new Date().toLocaleTimeString()}</span>
    `;
    return messageDiv;
}

/**
 * Escape HTML to prevent XSS attacks
 */
function escapeHTML(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Get AI-generated project summary
 */
async function getProjectSummary() {
    const summaryContainer = document.getElementById("summary-container");

    try {
        summaryContainer.innerHTML = '<p style="text-align: center; color: #999;">⏳ Generating summary...</p>';

        const data = await api.getProjectSummary();
        const summary = data.summary || "No summary available";

        summaryContainer.innerHTML = `
            <div class="summary-box">
                <h3>📊 Project Summary</h3>
                <p>${escapeHTML(summary)}</p>
                <p style="font-size: 12px; color: #999; margin-top: 10px;">
                    Generated: ${new Date().toLocaleString()}
                </p>
            </div>
        `;
    } catch (error) {
        summaryContainer.innerHTML = `<p style="color: red;">❌ Error: ${Utils.getErrorMessage(error)}</p>`;
        console.error("Summary error:", error);
    }
}

/**
 * Add new task
 */
async function addNewTask() {
    const taskData = {
        task_name: document.getElementById("task-name").value.trim(),
        assigned_to: document.getElementById("assigned-to").value.trim(),
        start_date: document.getElementById("start-date").value,
        end_date: document.getElementById("end-date").value,
        status: document.getElementById("task-status").value,
        client: document.getElementById("client").value.trim(),
    };

    // Validation
    if (!taskData.task_name || !taskData.assigned_to) {
        Utils.showNotification("⚠️ Task name and assignee are required", "error");
        return;
    }

    try {
        const result = await api.createTask(taskData);
        Utils.showNotification("✅ Task created successfully!", "success");
        document.getElementById("task-form").reset();
        await loadTasks();
    } catch (error) {
        Utils.showNotification(`❌ Failed to create task: ${Utils.getErrorMessage(error)}`, "error");
        console.error("Task creation error:", error);
    }
}

/**
 * Edit task (placeholder)
 */
async function editTask(taskId) {
    Utils.showNotification("ℹ️ Edit feature coming soon", "info");
    console.log("Edit task:", taskId);
}

/**
 * Delete task
 */
async function deleteTask(taskId) {
    if (!confirm("Are you sure you want to delete this task?")) return;

    try {
        await api.deleteTask(taskId);
        Utils.showNotification("✅ Task deleted successfully!", "success");
        await loadTasks();
    } catch (error) {
        Utils.showNotification(`❌ Failed to delete task: ${Utils.getErrorMessage(error)}`, "error");
    }
}

/**
 * Set up auto-refresh mechanism
 */
function setupAutoRefresh() {
    autoRefreshInterval = setInterval(() => {
        updateHealthStatus();
        loadTasks();
    }, CONFIG.UI.AUTO_REFRESH_INTERVAL);
}

/**
 * Attach event listeners
 */
function setupEventListeners() {
    const userInput = document.getElementById("user-input");

    // Send message on Enter key
    userInput.addEventListener("keypress", (event) => {
        if (event.key === "Enter" && !event.shiftKey) {
            event.preventDefault();
            sendMessage();
        }
    });
}

/**
 * Clean up resources on page unload
 */
window.addEventListener("beforeunload", () => {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
});

/**
 * Initialize app when DOM is ready
 */
document.addEventListener("DOMContentLoaded", initializeApp);

console.log('✅ app.js loaded, ready to initialize');
