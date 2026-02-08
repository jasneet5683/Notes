import { API_BASE_URL } from './config.js';

// Global state
let conversationHistory = [];

// 🔍 1. HEALTH CHECK ENDPOINT
async function checkHealth() {
    try {
        const response = await fetch(`${API_BASE_URL}/health`);
        const data = await response.json();
        
        const healthElement = document.getElementById('healthStatus');
        healthElement.textContent = `✅ ${data.service} - ${data.status.toUpperCase()}`;
        healthElement.className = 'health-indicator health-online';
        
        console.log('Health check:', data);
        return true;
    } catch (error) {
        console.error('Health check failed:', error);
        const healthElement = document.getElementById('healthStatus');
        healthElement.textContent = '❌ API OFFLINE - Check network connection';
        healthElement.className = 'health-indicator health-offline';
        return false;
    }
}

// 📊 2. GET PROJECT SUMMARY
async function getSummary() {
    try {
        document.getElementById('summaryDisplay').innerHTML = '<div class="loading">🔄 Generating AI summary...</div>';
        
        const response = await fetch(`${API_BASE_URL}/summary`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        document.getElementById('summaryDisplay').innerHTML = 
            `<div class="summary-box">
                <h3>🧠 AI Project Summary</h3>
                <p>${data.summary}</p>
                <small>Generated: ${new Date(data.timestamp).toLocaleString()}</small>
            </div>`;
    } catch (error) {
        console.error('Summary error:', error);
        document.getElementById('summaryDisplay').innerHTML = 
            '<div class="error">❌ Failed to generate summary. Check API connection.</div>';
    }
}

// 📋 3. GET ALL TASKS
async function loadAllTasks() {
    try {
        document.getElementById('taskList').innerHTML = '<div class="loading">🔄 Loading all tasks...</div>';
        
        const response = await fetch(`${API_BASE_URL}/tasks`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        console.log('Loaded tasks:', data);
        
        if (data.tasks && data.tasks.length > 0) {
            document.getElementById('taskList').innerHTML = `
                <div style="margin-bottom: 15px; color: #666;">
                    📊 Total Tasks: <strong>${data.count}</strong> | Last Updated: ${new Date(data.timestamp).toLocaleString()}
                </div>
                ${data.tasks.map(task => createTaskCard(task)).join('')}
            `;
        } else {
            document.getElementById('taskList').innerHTML = '<div class="loading">📝 No tasks found. Create your first task above!</div>';
        }
    } catch (error) {
        console.error('Load tasks error:', error);
        document.getElementById('taskList').innerHTML = '<div class="error">❌ Failed to load tasks. Check API connection.</div>';
    }
}

// 🆕 4. CREATE TASK (POST)
document.getElementById('taskForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const taskData = {
        task_name: document.getElementById('taskName').value.trim(),
        assigned_to: document.getElementById('assignedTo').value.trim(),
        client: document.getElementById('client').value.trim() || 'Not specified',
        start_date: document.getElementById('startDate').value || null,
        end_date: document.getElementById('endDate').value || null,
        status: document.getElementById('status').value,
        notify_email: document.getElementById('notifyEmail').value.trim() || null
    };
    
    try {
        const submitButton = e.target.querySelector('button');
        submitButton.textContent = '⏳ Creating...';
        submitButton.disabled = true;
        
        const response = await fetch(`${API_BASE_URL}/tasks`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(taskData)
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showNotification(result.message, 'success');
            document.getElementById('taskForm').reset();
            loadAllTasks(); // Refresh the task list
        } else {
            throw new Error(result.detail || 'Failed to create task');
        }
    } catch (error) {
        console.error('Create task error:', error);
        showNotification('❌ Failed to create task: ' + error.message, 'error');
    } finally {
        const submitButton = e.target.querySelector('button');
        submitButton.textContent = '🚀 Create Task';
        submitButton.disabled = false;
    }
});

// ✏️ 5. UPDATE TASK STATUS (PUT)
async function updateTaskStatus(taskName, newStatus) {
    try {
        const response = await fetch(`${API_BASE_URL}/tasks/${encodeURIComponent(taskName)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ new_status: newStatus })
        });
        
        const result = await response.json();
        
        if (response.ok) {
            showNotification(result.message, 'success');
            loadAllTasks(); // Refresh to show updated status
        } else {
            throw new Error(result.detail || 'Failed to update task');
        }
    } catch (error) {
        console.error('Update task error:', error);
        showNotification('❌ Failed to update task: ' + error.message, 'error');
    }
}

// 🔍 6. SEARCH TASKS
async function searchTasks() {
    const query = document.getElementById('searchInput').value.trim();
    if (!query) {
        showNotification('⚠️ Please enter a search term', 'error');
        return;
    }
    
    try {
        document.getElementById('searchResults').innerHTML = '<div class="loading">🔍 Searching...</div>';
        
        const response = await fetch(`${API_BASE_URL}/tasks/search?query=${encodeURIComponent(query)}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        console.log('Search results:', data);
        
        if (data.results && data.results.length > 0) {
            document.getElementById('searchResults').innerHTML = `
                <div style="margin-bottom: 15px; color: #666;">
                    🔍 Found <strong>${data.count}</strong> results for "${data.query}"
                </div>
                ${data.results.map(task => createTaskCard(task)).join('')}
            `;
        } else {
            document.getElementById('searchResults').innerHTML = 
                `<div class="loading">🚫 No results found for "${query}". Try different keywords.</div>`;
        }
    } catch (error) {
        console.error('Search error:', error);
        document.getElementById('searchResults').innerHTML = '<div class="error">❌ Search failed. Check API connection.</div>';
    }
}

// 🤖 7. CHAT WITH AI
function sendChat(event) {
    event.preventDefault();
    
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    if (!message) return;
    
    const messagesDiv = document.getElementById('chatMessages');
    
    // Add user message
    messagesDiv.innerHTML += `<div class="message user">👤 ${message}</div>`;
    input.value = '';
    
    // Add loading indicator
    const loadingId = 'loading_' + Date.now();
    messagesDiv.innerHTML += `<div id="${loadingId}" class="message bot">🤖 Thinking...</div>`;
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    
    // Send to API
    fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_message: message,
            conversation_history: conversationHistory
        })
    })
    .then(response => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
    })
    .then(data => {
        // Remove loading message
        document.getElementById(loadingId).remove();
        
        // Add AI response
        messagesDiv.innerHTML += `<div class="message bot">🤖 ${data.response}</div>`;
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
        
        // Update conversation history
        conversationHistory.push(
            { role: 'user', content: message },
            { role: 'assistant', content: data.response }
        );
        
        // Keep only last 10 messages to prevent payload getting too large
        if (conversationHistory.length > 10) {
            conversationHistory = conversationHistory.slice(-10);
        }
    })
    .catch(error => {
        console.error('Chat error:', error);
        document.getElementById(loadingId).remove();
        messagesDiv.innerHTML += `<div class="message bot">🤖 ❌ Sorry, I'm currently unavailable. Please try again later.</div>`;
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    });
}

// 🛠️ UTILITY FUNCTIONS

function createTaskCard(task) {
    return `
        <div class="task-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <h3 style="margin: 0; color: #333;">${task.task_name}</h3>
                <span class="status ${task.status?.toLowerCase().replace(' ', '-')}">${task.status}</span>
            </div>
            <p style="margin: 5px 0;"><strong>👤 Assigned to:</strong> ${task.assigned_to}</p>
            <p style="margin: 5px 0;"><strong>🏢 Client:</strong> ${task.client || 'Not specified'}</p>
            <p style="margin: 5px 0;"><strong>📧 Notify:</strong> ${task.notify_email || 'None'}</p>
            <p style="margin: 5px 0;"><strong>📅 Duration:</strong> ${task.start_date || 'No start'} → ${task.end_date || 'No end'}</p>
            <div style="margin-top: 15px;">
                <label style="font-weight: 600;">Update Status:</label>
                <select onchange="updateTaskStatus('${task.task_name}', this.value)" style="margin-top: 5px;">
                    <option value="${task.status}" selected>Current: ${task.status}</option>
                    <option value="Pending">📋 Pending</option>
                    <option value="In Progress">⚡ In Progress</option>
                    <option value="Completed">✅ Completed</option>
                </select>
            </div>
        </div>
    `;
}

function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = type;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed; top: 20px; right: 20px; z-index: 1000;
        padding: 15px 20px; border-radius: 8px; font-weight: 600;
        animation: slideIn 0.3s ease;
    `;
    
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 4000);
}

function clearTasksList() {
    document.getElementById('taskList').innerHTML = '<div class="loading">📝 Task list cleared. Click "Refresh Tasks" to reload.</div>';
}

// 🚀 INITIALIZATION
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Notes App initialized');
    console.log('🌐 API Base URL:', API_BASE_URL);
    
    checkHealth();
    loadAllTasks();
    getSummary();
});

// 🌐 GLOBAL FUNCTIONS (for onclick handlers)
window.checkHealth = checkHealth;
window.getSummary = getSummary;
window.loadAllTasks = loadAllTasks;
window.searchTasks = searchTasks;
window.sendChat = sendChat;
window.updateTaskStatus = updateTaskStatus;
window.clearTasksList = clearTasksList;
