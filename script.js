import { API_BASE_URL } from './config.js';

// Global state
let conversationHistory = [];
let allTasksData = []; // <--- 🆕 Add this to store tasks for export

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
    // 🔍 1. Identify the container
    const summaryDisplay = document.getElementById('summaryDisplay');
    
    // 🔍 2. GUARD: If the element is not on this page (like tasks.html), exit now!
    if (!summaryDisplay) {
        console.log("Summary display not found. Skipping AI analysis.");
        return; 
    }

    try {
        // 🔍 3. Check if we actually have data to analyze
        if (!allTasksData || allTasksData.length === 0) {
            summaryDisplay.innerHTML = '<div class="loading">⏳ Waiting for task data to arrive...</div>';
            return;
        }

        summaryDisplay.innerHTML = '<div class="loading">📊 AI is analyzing priorities, deadlines & workload...</div>';

        // 4. Calculate Hard Facts (Logic stays the same)
        const total = allTasksData.length;
        const pending = allTasksData.filter(t => (t.status||'').toLowerCase().includes('pending')).length;
        const progress = allTasksData.filter(t => (t.status||'').toLowerCase().includes('progress')).length;
        const completed = allTasksData.filter(t => (t.status||'').toLowerCase().includes('completed')).length;
        const hold = allTasksData.filter(t => (t.status||'').toLowerCase().includes('hold')).length;
        const cancelled = allTasksData.filter(t => (t.status||'').toLowerCase().includes('cancelled')).length;

        // 5. Prepare data for AI
        const detailedTasks = allTasksData.map(t => ({
            task: t.Task_Name,
            status: t.status,
            assignee: t.assigned_to || "Unassigned",
            priority: t.Priority || "N/A",
            start: t.start_date || "N/A",
            due: t.end_date || "N/A",
            client: t.Client || "General"
        }));

        const prompt = `
            I need a professional Project Status Report.
            HARD DATA SUMMARY:
            - Total Tasks: ${total} | Pending: ${pending} | In Progress: ${progress} | Completed: ${completed}
            DETAILED TASK LIST (JSON):
            ${JSON.stringify(detailedTasks)}
            INSTRUCTIONS: Write a concise summary (max 150 words) covering Blockers, Workload, and Progress.
        `;

        // 6. Send to Backend
        const response = await fetch(`${API_BASE_URL}/ask`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: prompt })
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        const aiText = data.answer || data.response || "No summary generated.";

        // 7. Render Output Safely
        summaryDisplay.innerHTML = 
            `<div class="summary-box">
                <h3>🧠 Smart Project Analysis</h3>
                <div class="stats-bar" style="display:flex; gap:15px; margin-bottom:15px; padding-bottom:10px; border-bottom:1px solid #eee; font-size:0.9rem;">
                    <span><b>Total:</b> ${total}</span>
                    <span style="color:#e67e22"><b>Pending:</b> ${pending}</span>
                    <span style="color:#17a2b8"><b>Progress:</b> ${progress}</span>
                    <span style="color:#28a745"><b>Done:</b> ${completed}</span>
                </div>
                <div class="ai-content" style="line-height: 1.6;">
                    ${typeof marked !== 'undefined' ? marked.parse(aiText) : aiText.replace(/\n/g, '<br>')}
                </div>
                <div style="margin-top:10px; text-align:right; font-size:0.8rem; color:#888;">
                    Generated: ${new Date().toLocaleTimeString()}
                </div>
            </div>`;

    } catch (error) {
       console.error('Summary error:', error);
        // Use the variable summaryDisplay here, not document.getElementById
        if (summaryDisplay) {
            summaryDisplay.innerHTML = `<div class="error">❌ Analysis Failed: ${error.message}</div>`;
        }
    }
}

// 📋 3. GET ALL TASKS
async function loadAllTasks() {
    const taskListElement = document.getElementById('taskList');
    
    try {
        if (taskListElement) {
            taskListElement.innerHTML = '<div class="loading">🔄 Loading tasks...</div>';
        }
        
        const response = await fetch(`${API_BASE_URL}/tasks`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        
        // ✅ CRITICAL: Save to the global variable so charts can see it
        allTasksData = data.tasks || []; 
        console.log('Data synced to allTasksData:', allTasksData);
      
        // 🚀 TRIGGER THE DROPDOWN UPDATE HERE
        if (typeof populateClientDropdown === 'function') {
        populateClientDropdown(allTasksData);
        }

        
        // Render List (if on Tasks page)
        if (taskListElement) {
            if (allTasksData.length > 0) {
                taskListElement.innerHTML = allTasksData.map(task => createTaskCard(task)).join('');
            } else {
                taskListElement.innerHTML = '<div class="loading">No tasks found.</div>';
            }
        }

        // ✅ AUTO-REFRESH CHARTS (if on Dashboard)
        // This replaces the manual "Refresh Data" button requirement
        if (document.getElementById('statusChart')) renderStatusChart();
        if (document.getElementById('resourceChart')) renderResourceChart();

    } catch (error) {
        console.error('Load tasks error:', error);
    }
}

// --- 🆕 4. CREATE TASK (POST) ---
// We check if 'taskForm' exists before adding the listener
const taskFormElement = document.getElementById('taskForm');

if (taskFormElement) {
    taskFormElement.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const taskData = {
            task_name: document.getElementById('taskName').value.trim(),
            assigned_to: document.getElementById('assignedTo').value.trim(),
            client: document.getElementById('client').value.trim() || 'Not specified',
            start_date: document.getElementById('startDate').value || null,
            end_date: document.getElementById('endDate').value || null,
            status: document.getElementById('status').value,
            priority: String(document.getElementById('priority').value || "1"),
            notify_email: document.getElementById('notifyEmail').value.trim() || null,
            predecessor: document.getElementById('predecessor').value 
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
                // Use a standard alert or your showNotification function
                alert(result.message || 'Task Created Successfully! ✨');
                taskFormElement.reset();
                
                // Only try to refresh the list if we are on the page that has it
                if (document.getElementById('taskList')) {
                    loadAllTasks(); 
                }
            } else {
                throw new Error(result.detail || 'Failed to create task');
            }
        } catch (error) {
            console.error('Create task error:', error);
            alert('❌ Failed to create task: ' + error.message);
        } finally {
            const submitButton = e.target.querySelector('button');
            submitButton.textContent = '🚀 Create Task';
            submitButton.disabled = false;
        }
    });
}

// ✏️ 5. UPDATE TASK STATUS (PUT)
async function updateTaskStatus(taskName, newStatus) {
    try {
        const response = await fetch(`${API_BASE_URL}/tasks/${encodeURIComponent(taskName)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_name: taskName, new_status: newStatus })
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

// 🤖 7. CHAT WITH AI (UPDATED FOR CHARTS/TABLES)
function sendChat(event) {
    if (event) event.preventDefault();
    
    const input = document.getElementById('chatInput');
    const message = input.value.trim();
    if (!message) return;
    
    const messagesDiv = document.getElementById('chatMessages');
    
    // Add user message
    messagesDiv.innerHTML += `<div class="message user">👤 ${message}</div>`;
    input.value = '';
    
    // Add loading indicator
    const loadingId = 'loading_' + Date.now();
    const loadingDiv = document.createElement('div');
    loadingDiv.id = loadingId;
    loadingDiv.className = 'message bot';
    loadingDiv.innerText = '🤖 Thinking...';
    messagesDiv.appendChild(loadingDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
    
    // Prepare payload
    const requestPayload = {
        prompt: message,
        conversation_history: conversationHistory.map(msg => ({
            role: msg.role,
            content: typeof msg.content === 'string' ? msg.content : JSON.stringify(msg.content)
        }))
    };
    
    // Send to API
    fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestPayload)
    })
    .then(response => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
    })
    .then(data => {
        // 1. Remove loading message
        const loadingElement = document.getElementById(loadingId);
        if (loadingElement) loadingElement.remove();
        
        // 2. Add AI response using smart renderer (Handles Charts/Tables)
        renderAIMessage(data.response, messagesDiv);
        
        // 3. Update conversation history
        conversationHistory.push(
            { role: 'user', content: message },
            { role: 'assistant', content: data.response }
        );
        
        // Trim history
        if (conversationHistory.length > 10) {
            conversationHistory = conversationHistory.slice(-10);
        }
    })
    .catch(error => {
        console.error('Chat error:', error);
        const loadingElement = document.getElementById(loadingId);
        if (loadingElement) loadingElement.remove();
        messagesDiv.innerHTML += `<div class="message bot">🤖 ❌ Sorry, I'm currently unavailable.</div>`;
        messagesDiv.scrollTop = messagesDiv.scrollHeight;
    });
}

// 🛠️ UTILITY FUNCTIONS
function createTaskCard(task) {
    const priorityEmoji = getPriorityEmoji(task.Priority);
    const formatDate = (dateStr) => {
        if (!dateStr) return 'Not set';
        return new Date(dateStr).toLocaleDateString();
    };
    
    return `
        <div class="task-card">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <h3 style="margin: 0; color: #333;">${task.Task_Name || 'Untitled Task'}</h3>
                <span class="status ${task.status?.toLowerCase().replace(' ', '-')}">${task.status}</span>
            </div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                <span style="font-size: 14px; color: #666;">Priority: ${priorityEmoji} ${task.Priority || 1}</span>
                <span style="font-size: 12px; color: #999;">Task ID: ${task.Task_Name?.substring(0, 8)}...</span>
            </div>
            <p style="margin: 5px 0;"><strong>👤 Assigned to:</strong> ${task.assigned_to || 'Unassigned'}</p>
            <p style="margin: 5px 0;"><strong>🏢 Client:</strong> ${task.Client || 'Not specified'}</p>
            <p style="margin: 5px 0;"><strong>📅 Start Date:</strong> ${formatDate(task.start_date)}</p>
            <p style="margin: 5px 0;"><strong>📅 End Date:</strong> ${formatDate(task.end_date)}</p>
            <div style="margin-top: 15px;">
                <label style="font-weight: 600;">Update Status:</label>
                <select onchange="updateTaskStatus('${task.Task_Name}', this.value)" style="margin-top: 5px; width: 100%; padding: 5px;">
                    <option value="${task.status}" selected>Current: ${task.status}</option>
                    <option value="Pending">📋 Pending</option>
                    <option value="In Progress">⚡ In Progress</option>
                    <option value="Completed">✅ Completed</option>
                    <option value="On Hold">⏸️ On Hold</option>
                    <option value="Cancelled">❌ Cancelled</option>
                </select>
            </div>
        </div>
    `;
}


/**
 * 🎨 HELPER: Renders AI Text, Tables, and Charts with DYNAMIC COLORS
 */
function renderAIMessage(content, container) {
    const msgDiv = document.createElement('div');
    msgDiv.className = 'message bot';

    let textContent = content; 
    let taskPreviewData = null;
    let chartJsonString = null;

    // --- 1. EXTRACT TASK PREVIEW (Triggered ONLY by ui_type) ---
    const potentialJsonMatch = textContent.match(/\{[\s\S]*\}/);
    if (potentialJsonMatch) {
        try {
            const rawJson = potentialJsonMatch[0];
            const parsed = JSON.parse(rawJson);
            
            // CRITICAL CHECK: Only show the "Add" card if ui_type is TASK_ADDITION
            if (parsed.ui_type === "TASK_ADDITION") {
                taskPreviewData = parsed;
                // Clean the text: Remove the JSON block from the chat bubble
                textContent = textContent.replace(rawJson, "").replace("TASK_PREVIEW_JSON:", "").trim();
            }
        } catch (e) {
            // Not valid JSON or not the right type, let other logic handle it
        }
    }

    // --- 2. EXTRACT MERMAID (Original Logic Preserved) ---
    const mermaidRegex = /```mermaid\s*([\s\S]*?)\s*```/;
    const mermaidMatch = textContent.match(mermaidRegex);
    if (mermaidMatch) {
        const mermaidSyntax = mermaidMatch[1].trim();
        textContent = textContent.replace(mermaidMatch[0], "").trim();
        if (textContent === "") {
            textContent = "I've updated the **Project Visualization** section with the requested diagram! 📊✨";
        }
        if (typeof renderMermaid === "function") {
            renderMermaid(mermaidSyntax);
        }
    }

    // --- 3. EXTRACT CHART JSON (Original Logic Preserved) ---
    // Note: Charts use 'is_chart' or 'chart_type', so they won't trigger Section 1
    const codeBlockRegex = /```(json|chart)\s*([\s\S]*?)\s*```/;
    const chartMatch = textContent.match(codeBlockRegex);
    if (chartMatch) {
        try {
            const potentialJson = chartMatch[2];
            const parsed = JSON.parse(potentialJson);
            if (parsed.is_chart || parsed.chart_type) {
                chartJsonString = potentialJson;
                textContent = textContent.replace(chartMatch[0], "").trim();
            }
        } catch (e) {}
    } else {
        const openBrace = textContent.indexOf('{');
        const closeBrace = textContent.lastIndexOf('}');
        if (openBrace !== -1 && closeBrace > openBrace) {
            try {
                const potentialJson = textContent.substring(openBrace, closeBrace + 1);
                const parsed = JSON.parse(potentialJson);
                if (parsed.is_chart || parsed.chart_type) {
                    chartJsonString = potentialJson;
                    textContent = textContent.substring(0, openBrace).trim();
                }
            } catch (e) {}
        }
    }

    // --- 4. RENDER FINAL TEXT ---
    msgDiv.innerHTML = marked.parse(textContent);

    // --- 5. APPEND CHART (Original Config Preserved) ---
    if (chartJsonString) {
        const canvasId = "chart-" + Date.now();
        const chartContainer = document.createElement("div");
        chartContainer.className = "chart-wrapper";
        chartContainer.style.cssText = "margin-top: 15px; height: 300px;";
        chartContainer.innerHTML = `<canvas id="${canvasId}"></canvas>`;
        msgDiv.appendChild(chartContainer);

        setTimeout(() => {
            try {
                const parsedJson = JSON.parse(chartJsonString);
                const ctx = document.getElementById(canvasId).getContext('2d');
                new Chart(ctx, {
                    type: parsedJson.chart_type || 'bar',
                    data: {
                        labels: parsedJson.data.labels,
                        datasets: [{
                            label: parsedJson.title || "Data",
                            data: parsedJson.data.values,
                            backgroundColor: ['rgba(54, 162, 235, 0.6)', 'rgba(255, 99, 132, 0.6)', 'rgba(255, 206, 86, 0.6)', 'rgba(75, 192, 192, 0.6)', 'rgba(153, 102, 255, 0.6)'],
                            borderWidth: 1
                        }]
                    },
                    options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true } } }
                });
            } catch (e) { console.error("Chart Render Error:", e); }
        }, 0);
    }

    // --- 6. APPEND TASK PREVIEW CARD ---
   // --- UPDATED TASK PREVIEW CARD (Including Start Date) ---
if (taskPreviewData) {
    const previewCard = document.createElement('div');
    previewCard.className = 'task-preview-card';
    previewCard.style.cssText = "border: 2px solid #3b82f6; border-radius: 12px; padding: 15px; background: #ffffff; margin-top: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05);";
    
    // Logic to handle if start_date is missing (as a fallback)
    const displayStart = taskPreviewData.start_date || new Date().toISOString().split('T')[0];

    previewCard.innerHTML = `
        <div style="font-weight: bold; margin-bottom: 10px; color: #1e293b; display: flex; align-items: center; gap: 8px;">
            <span style="font-size: 1.2rem;">📋</span> Review New Task
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; font-size: 0.85rem; color: #475569;">
            <div><small style="color: #94a3b8; display: block;">TASK NAME</small><b>${taskPreviewData.task_name}</b></div>
            <div><small style="color: #94a3b8; display: block;">ASSIGNEE</small><b>${taskPreviewData.assigned_to}</b></div>
            
            <div><small style="color: #94a3b8; display: block;">START DATE</small><b>${displayStart}</b></div>
            
            <div><small style="color: #94a3b8; display: block;">DUE DATE</small><b>${taskPreviewData.end_date}</b></div>
            <div><small style="color: #94a3b8; display: block;">CLIENT</small><b>${taskPreviewData.client}</b></div>
        </div>
        <div style="margin-top: 15px; display: flex; gap: 10px;">
            <button class="confirm-btn" style="flex: 1; background: #2563eb; color: white; border: none; padding: 8px; border-radius: 6px; cursor: pointer; font-weight: 600;">Confirm & Add</button>
            <button class="cancel-btn" style="background: #f1f5f9; color: #64748b; border: none; padding: 8px 12px; border-radius: 6px; cursor: pointer;">Cancel</button>
        </div>
    `;

    // Ensure the data passed to the confirm function includes the assumed start date
    const finalData = { ...taskPreviewData, start_date: displayStart };

    previewCard.querySelector('.confirm-btn').onclick = () => confirmTaskToSheet(finalData, previewCard.querySelector('.confirm-btn'));
    previewCard.querySelector('.cancel-btn').onclick = () => previewCard.remove();
    
    msgDiv.appendChild(previewCard);
}

    container.appendChild(msgDiv);
    container.scrollTop = container.scrollHeight;
}

// --- END OF FUNCTION renderAIMessage ---
// Make sure no other code (like smartColorize) is accidentally inside this function!

/**
 * 🌈 SMART COLOR GENERATOR
 * Assigns specific colors to known statuses/priorities
 * and generates a nice palette for everything else.
 */
function smartColorize(chartJson) {
    // 1. Define Standard Brand Colors
    const colorMap = {
        // Statuses
        'completed': '#2ecc71',   // Green
        'done': '#2ecc71',
        'in progress': '#3498db', // Blue
        'pending': '#f1c40f',     // Yellow/Orange
        'on hold': '#95a5a6',     // Grey
        'cancelled': '#e74c3c',   // Red
        
        // Priorities
        'critical': '#c0392b',    // Dark Red
        'blocker': '#800000',     // Maroon
        'high': '#e67e22',        // Orange
        'medium': '#f1c40f',      // Yellow
        'low': '#27ae60',         // Green
        'info': '#3498db',        // Blue

        // Clients (Examples)
        'etisalat': '#71bc68',
        'du': '#00a9ce',
        'batelco': '#d6001c'
    };

    // 2. Fallback Palette (Pastel/Vibrant mix)
    const fallbackPalette = [
        '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', 
        '#C9CBCF', '#FFCD56', '#4D5360', '#F7464A', '#46BFBD'
    ];

    // 3. Apply colors to datasets
    if (chartJson.data && chartJson.data.datasets) {
        chartJson.data.datasets.forEach(dataset => {
            // We need to generate a color array matching the labels
            const backgroundColors = chartJson.data.labels.map((label, index) => {
                const key = label.toLowerCase().trim();
                // Check if we have a specific color for this label
                if (colorMap[key]) {
                    return colorMap[key];
                }
                // Otherwise, pick from the fallback palette (looping if needed)
                return fallbackPalette[index % fallbackPalette.length];
            });

            dataset.backgroundColor = backgroundColors;
            // Add a slight border for better visibility
            dataset.borderColor = '#ffffff'; 
            dataset.borderWidth = 1;
        });
    }

    // 4. MODERN STYLING 🎨
    if (!chartJson.options) chartJson.options = {};
    
    // Make it responsive
    chartJson.options.responsive = true;
    chartJson.options.maintainAspectRatio = false;
    // A. If it's a BAR chart, make corners round and clean up grid
    if (chartJson.type === 'bar') {
        chartJson.data.datasets.forEach(dataset => {
            dataset.borderRadius = 8; // Rounded top corners
            dataset.barThickness = 30; // Not too fat, not too thin
        });
        
        chartJson.options.scales = {
            y: { beginAtZero: true, grid: { color: '#f0f0f0' } }, // Faint grid
            x: { grid: { display: false } } // Remove vertical grid lines
        };
    }
    // B. If it's a PIE chart, turn it into a DOUGHNUT for a modern look
    if (chartJson.type === 'pie' || chartJson.type === 'doughnut') {
        chartJson.type = 'doughnut'; // Force doughnut style
        chartJson.options.cutout = '70%'; // Thinner ring
        chartJson.options.plugins = {
            legend: { position: 'right' } // Legend on the side looks better
        };
    }
    return chartJson;
}



function getPriorityEmoji(priority) {
    // 1. Convert to string safely
    // 2. Remove extra spaces (.trim)
    // 3. Make lowercase (.toLowerCase)
    const p = String(priority || '').trim().toLowerCase();

    // Debugging: Check the console to see exactly what the code sees
    // console.log(`Priority detected: "${p}"`); 

    switch (p) {
        case 'low':      return '🟢';
        case 'medium':   return '🟡';
        case 'high':     return '🟠';
        case 'critical': return '🔴';
        case 'blocker':  return '⛔';
        case 'info':     return '🔵';
        default:         return '⚪'; // Still white? Check the console log above!
    }
}


function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = type;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed; top: 20px; right: 20px; z-index: 1000;
        padding: 15px 20px; border-radius: 8px; font-weight: 600;
        animation: slideIn 0.3s ease; max-width: 350px;
        ${type === 'success' ? 'background: #d4edda; color: #155724; border: 1px solid #c3e6cb;' : ''}
        ${type === 'error' ? 'background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb;' : ''}
    `;
    
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 4000);
}

function clearTasksList() {
    document.getElementById('taskList').innerHTML = '<div class="loading">📝 Task list cleared. Click "Refresh Tasks" to reload.</div>';
}

// 🚀 INITIALIZATION
document.addEventListener('DOMContentLoaded', () => {
    console.log('🚀 Task Management App initialized');
    console.log('🌐 API Base URL:', API_BASE_URL);
    
    // Add CSS for animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideIn {
            from { transform: translateX(100%); opacity: 0; }
            to { transform: translateX(0); opacity: 1; }
        }
        .task-card {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 10px;
            background: #f9f9f9;
            transition: box-shadow 0.2s ease;
        }
        .task-card:hover {
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .status {
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: bold;
        }
        .status.completed { background: #d4edda; color: #155724; }
        .status.in-progress { background: #fff3cd; color: #856404; }
        .status.pending { background: #f8d7da; color: #721c24; }
    `;
    document.head.appendChild(style);
    
    checkHealth();
    loadAllTasks();
    getSummary();
});

// 📥 EXPORT TASKS TO CSV
function downloadTasksCSV() {
    if (!allTasksData || allTasksData.length === 0) {
        showNotification("⚠️ No tasks available to export.", "error");
        return;
    }

    // 1. Define Headers
    const headers = ["Task Name", "Assigned To", "Client", "Priority", "Status", "Start Date", "End Date"];
    
    // 2. Map Data to Rows
    const rows = allTasksData.map(task => [
        `"${task.Task_Name || ''}"`,       // Wrap in quotes to handle commas in text
        `"${task.assigned_to || ''}"`,
        `"${task.Client || ''}"`,
        task.Priority || 1,
        `"${task.status || ''}"`,
        task.start_date || '',
        task.end_date || ''
    ]);

    // 3. Combine Headers and Rows
    const csvContent = [headers.join(","), ...rows.map(r => r.join(","))].join("\n");

    // 4. Create Download Link
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `project_tasks_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// 📥 DOWNLOAD SUMMARY AS TEXT
function downloadSummary() {
    const summaryBox = document.querySelector('.summary-box p'); // Select the paragraph inside the summary box
    
    if (!summaryBox) {
        showNotification("⚠️ No summary generated yet.", "error");
        return;
    }

    const textContent = `🧠 AI PROJECT SUMMARY\nDate: ${new Date().toLocaleString()}\n\n${summaryBox.innerText}`;
    
    // Create Download Link
    const blob = new Blob([textContent], { type: "text/plain;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `project_summary_${new Date().toISOString().split('T')[0]}.txt`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// ==========================================
// 📊 CHART VISUALIZATION
// ==========================================

let myChart = null; // Variable to store chart instance

function renderStatusChart() {
    // 1. Check if we have data
    //if (typeof allTasksData === 'undefined' || !allTasksData || allTasksData.length === 0) {
    //    alert("⚠️ No data found! Please click 'Refresh Data' first.");
     //   return;
    const chartCanvas = document.getElementById('statusChart');
    if (!chartCanvas) return; 
    // ✅ Change the alert to a silent check
    if (!allTasksData || allTasksData.length === 0) {
        console.log("Waiting for data to load before rendering Status Chart...");
        return;
    }
    

    // 2. Count the statuses
    // --- FIX: We must declare ALL variables here first ---
    let pending = 0;
    let inProgress = 0;
    let completed = 0;
    let onHold = 0;      
    let cancelled = 0;   

    allTasksData.forEach(task => {
        let status = (task.status || "").toLowerCase(); 
        
        if (status.includes("pending")) pending++;
        else if (status.includes("progress")) inProgress++;
        else if (status.includes("completed")) completed++;
        else if (status.includes("hold")) onHold++;       
        else if (status.includes("cancelled")) cancelled++; 
    });

    // 3. Get Canvas Context
    const ctx = document.getElementById('statusChart').getContext('2d');

    // 4. Destroy previous chart if it exists
    if (myChart) {
        myChart.destroy();
    }

    // 5. Create New Chart
    myChart = new Chart(ctx, {
        type: 'doughnut', 
        data: {
            // --- FIX: Add the new labels here ---
            labels: ['Pending', 'In Progress', 'Completed', 'On Hold', 'Cancelled'], 
            datasets: [{
                label: '# of Tasks',
                // --- FIX: Add the new counts here ---
                data: [pending, inProgress, completed, onHold, cancelled], 
                backgroundColor: [
                    '#ffc107', // Yellow (Pending)
                    '#17a2b8', // Blue (In Progress)
                    '#28a745', // Green (Completed)
                    '#6c757d', // Grey (On Hold)
                    '#dc3545'  // Red (Cancelled)
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom', // Moves labels to the bottom
                    labels: {
                        boxWidth: 12,
                        padding: 15
                    }
                }
            }
        }
    });
}

// Variable to store the chart instance so we can destroy/redraw it
let resourceChartInstance = null;

function renderResourceChart() {
  //  if (!allTasksData || allTasksData.length === 0) {
  //      alert("No data available. Please refresh.");
   //     return;
  //  }
 const chartCanvas = document.getElementById('resourceChart');
    if (!chartCanvas) return;
    // ✅ Change the alert to a silent check
    if (!allTasksData || allTasksData.length === 0) {
        console.log("Waiting for data to load before rendering Resource Chart...");
        return;
    }
    const ctx = document.getElementById('resourceChart');
    
    // 1. Process Data
    const clientCounts = {};
    allTasksData.forEach(task => {
        const client = (task.Client || 'General').trim();
        clientCounts[client] = (clientCounts[client] || 0) + 1;
    });

    const labels = Object.keys(clientCounts);
    const dataValues = Object.values(clientCounts);

    // 2. Destroy old chart to prevent glitches
    if (resourceChartInstance) {
        resourceChartInstance.destroy();
    }

    // 3. Draw Chart with Multiple Colors
    resourceChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Tasks Assigned',
                data: dataValues,
                // Pass an ARRAY of colors here:
                backgroundColor: [
                    'rgba(255, 99, 132, 0.7)',   // Red
                    'rgba(54, 162, 235, 0.7)',   // Blue
                    'rgba(255, 206, 86, 0.7)',   // Yellow
                    'rgba(75, 192, 192, 0.7)',   // Green
                    'rgba(153, 102, 255, 0.7)',  // Purple
                    'rgba(255, 159, 64, 0.7)',   // Orange
                    'rgba(201, 203, 207, 0.7)'   // Grey
                ],
                borderColor: [
                    'rgba(255, 99, 132, 1)',
                    'rgba(54, 162, 235, 1)',
                    'rgba(255, 206, 86, 1)',
                    'rgba(75, 192, 192, 1)',
                    'rgba(153, 102, 255, 1)',
                    'rgba(255, 159, 64, 1)',
                    'rgba(201, 203, 207, 1)'
                ],
                borderWidth: 1,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true, ticks: { stepSize: 1 } },
                x: { grid: { display: false } }
            },
            plugins: { legend: { display: false } }
        }
    });
}

// --- STEP 1: VOICE TO TEXT LOGIC ---

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition;
let isListening = false;

// Check if browser supports it
if (SpeechRecognition) {
    recognition = new SpeechRecognition();
    recognition.continuous = false; // Stop after one sentence
    recognition.lang = 'en-US';
    recognition.interimResults = true; // Show text AS you speak

    // 1. When Voice Starts
    recognition.onstart = function() {
        isListening = true;
        const btn = document.getElementById("btn-mic");
        const input = document.getElementById("chatInput");
        
        btn.classList.add("listening"); // Start Red Pulse
        input.placeholder = "Listening... Speak now...";
    };

    // 2. When Voice Ends
    recognition.onend = function() {
        isListening = false;
        const btn = document.getElementById("btn-mic");
        const input = document.getElementById("chatInput");
        
        btn.classList.remove("listening"); // Stop Pulse
        input.placeholder = "Type or speak...";
        
        // Optional: Auto-focus the input so you can edit if needed
        input.focus();
    };

    // 3. Handle the Result
    recognition.onresult = function(event) {
        let transcript = "";
        // Loop through results (handles mid-sentence pauses)
        for (let i = event.resultIndex; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript;
        }
        
        // Type it into the input box
        document.getElementById("chatInput").value = transcript;
    };
}

// Toggle Function (Clicking the Mic)
function toggleChatVoice() {
    if (!SpeechRecognition) {
        alert("Voice features are not supported in this browser. Try Chrome.");
        return;
    }

    if (isListening) {
        recognition.stop();
    } else {
        recognition.start();
    }
}

//dropdown for Mermaid charts
function populateClientDropdown(tasks) {
    const selector = document.getElementById('client-selector');
    if (!selector) return;

    // Use .Client with capital 'C' to match your Google Sheet
    const clients = [...new Set(tasks.map(t => t.Client))].filter(Boolean);
    
    // Reset and add 'All' option
    selector.innerHTML = '<option value="All">🌐 All Clients</option>';
    
    clients.sort().forEach(client => {
        const option = document.createElement('option');
        option.value = client;
        option.text = `🏢 ${client}`;
        selector.appendChild(option);
    });
}

//Mermaid functions
// Initialize Mermaid configuration
if (typeof mermaid !== 'undefined') {
    mermaid.initialize({ 
        startOnLoad: true,
        theme: 'neutral',
        securityLevel: 'loose',
        flowchart: { useMaxWidth: false, htmlLabels: true, curve: 'basis' },
        gantt: { useMaxWidth: false, barHeight: 30, fontSize: 12 }
    });
    console.log("Mermaid initialized successfully! ✅");
} else {
    console.warn("Mermaid library not found. Diagrams will not render. ⚠️");
}
/**
 * Fetches Mermaid code from the Railway API and renders it.
 * @param {string} type - The type of visualization (e.g., 'gantt' or 'flowchart')
 */
async function loadVisualization(type) {
    console.log("Fetching visualization for:", type);
    
    const container = document.getElementById('mermaid-container');
    if (!container) return;

    // Show loading state
    container.innerHTML = "🌀 Fetching data...";
    container.removeAttribute('data-processed');

    try {
        // Update this URL with your actual Railway deployment endpoint
        const API_URL = `${API_BASE_URL}/viz/${type}`; 
        const response = await fetch(API_URL);
        if (!response.ok) {
            throw new Error(`Network response was not ok: ${response.status}`);
        }
        const data = await response.json();
        if (data.mermaid_code) {
            // Inject the Mermaid syntax into the container
            container.innerHTML = data.mermaid_code;
            // Trigger the Mermaid rendering engine
            await mermaid.run({
                nodes: [container],
            });
        } else {
            container.innerHTML = "⚠️ No chart data found for this selection.";
        }
    } catch (err) {
        console.error("Critical Error:", err);
        container.innerHTML = "❌ Error: Could not load the project data. Please check the console.";
    }
}

// --- 📊 Mermaid ---
// --- 🌿 FLOWCHART (Multiple Arrows) ---
window.generateFlowchart = async function() {
    const container = document.getElementById('mermaid-container');
    try {
        const selectedClient = document.getElementById('client-selector').value;
        let filteredTasks = (selectedClient === "All") 
            ? allTasksData 
            : allTasksData.filter(t => String(t.Client) === selectedClient);

        // Map of IDs in current view for quick lookup
        const validIds = new Set(filteredTasks.map(t => String(t.task_id)));
        let chartSyntax = `graph LR\n`;

        filteredTasks.forEach(t => {
            const id = `T${t.task_id}`;
            const name = (t.Task_Name || "Task").replace(/[$$$$"']/g, "");
            const status = (t.status || "Pending").toUpperCase();

            // 1. Define the Node
            chartSyntax += `    ${id}["${name}<br/>(${status})"]\n`;

            // 2. ⚡ MULTIPLE PREDECESSORS LOGIC
            if (t.predecessor) {
                // Split by comma, trim spaces, and filter to ensure the ID exists in the view
                const preds = String(t.predecessor).split(',').map(p => p.trim());
                preds.forEach(pId => {
                    if (validIds.has(pId)) {
                        chartSyntax += `    T${pId} --> ${id}\n`;
                    }
                });
            }

            // 3. Styling
            if (status.includes('COMPLETE')) chartSyntax += `    style ${id} fill:#dcfce7,stroke:#16a34a\n`;
            else if (status.includes('PROGRESS')) chartSyntax += `    style ${id} fill:#dbeafe,stroke:#2563eb\n`;
            else if (status.includes('HOLD')) chartSyntax += `    style ${id} fill:#5a5a5a,stroke:#ffffff\n`;
        });

        renderMermaid(chartSyntax);
    } catch (err) {
        console.error("Flowchart Error:", err);
        container.innerHTML = `<p style="color:red;">Error rendering flowchart links.</p>`;
    }
};

// --- 📊 GANTT CHART (Multiple Dependencies) ---
window.generateGantt = async function() {
    const container = document.getElementById('mermaid-container');
    try {
        const selectedClient = document.getElementById('client-selector').value;
        let filteredTasks = (selectedClient === "All") 
            ? allTasksData 
            : allTasksData.filter(t => String(t.Client) === selectedClient);

        const validIds = new Set(filteredTasks.map(t => String(t.task_id)));

        let chartSyntax = `gantt
        title Timeline: ${selectedClient}
        dateFormat YYYY-MM-DD
        axisFormat %m/%d
        section Tasks\n`;

        filteredTasks.forEach(t => {
            const id = `ID${t.task_id}`;
            const name = (t.Task_Name || "Task").replace(/[$$$$"']/g, "");
            const start = t.start_date || "2024-01-01";
            const end = t.end_date || "2024-01-07";
            
            // ⚡ GANTT DEPENDENCY LOGIC
            // Mermaid Gantt typically uses 'after ID' for its flow.
            // If multiple exist, we link to the LAST one listed to ensure it waits for all.
            let timing = start;
            if (t.predecessor) {
                const preds = String(t.predecessor).split(',').map(p => p.trim()).filter(p => validIds.has(p));
                if (preds.length > 0) {
                    timing = `after ID${preds[preds.length - 1]}`; 
                }
            }
            
            let statusTag = "";
            const s = String(t.status || "").toLowerCase();
            if (s.includes('complete')) statusTag = "done,";
            else if (s.includes('progress')) statusTag = "active,";

            chartSyntax += `    ${name} :${statusTag} ${id}, ${timing}, ${end}\n`;
        });

        renderMermaid(chartSyntax);
    } catch (err) {
        console.error("Gantt Error:", err);
        container.innerHTML = `<p style="color:red;">Error rendering timeline dependencies.</p>`;
    }
};

// Global render function
async function renderMermaid(syntax) {
    const container = document.getElementById('mermaid-container');
    if (!container) return;

    // 1. Clear previous state and attributes
    container.innerHTML = ""; 
    container.removeAttribute('data-processed');

    // 2. Create a fresh inner div
    const chartDiv = document.createElement('div');
    chartDiv.className = 'mermaid';
    chartDiv.style.width = '100%';
    chartDiv.style.minHeight = '500px';
    chartDiv.textContent = syntax; // Using textContent prevents HTML injection issues
    container.appendChild(chartDiv);

    try {
        // 3. Use the modern run command (v10+)
        await mermaid.run({
            nodes: [chartDiv],
        });
        console.log("✅ Mermaid rendered successfully.");
    } catch (err) {
        console.error("❌ Mermaid Syntax Error:", err);
        container.innerHTML = `<div style="padding:20px; color:#b91c1c; background:#fee2e2; border-radius:8px;">
            <strong>Diagram Rendering Error:</strong><br/>
            <small>The AI generated invalid syntax. Try asking it to "fix the flowchart syntax".</small>
            <pre style="font-size:10px; margin-top:10px;">${syntax}</pre>
        </div>`;
    }
}


// --- 📸 EXPORT CHART AS IMAGE ---
window.exportChartAsImage = function() {
    const container = document.getElementById('mermaid-container');
    const originalSvg = container.querySelector('svg');

    if (!originalSvg) {
        alert("Please generate a chart first!");
        return;
    }

    try {
        // 1. Clone the SVG so we don't mess up the screen display
        const svgClone = originalSvg.cloneNode(true);
        svgClone.setAttribute("xmlns", "http://www.w3.org/2000/svg");

        // 2. 🛡️ SANITIZE: Remove external font imports that cause the "Taint"
        const styles = svgClone.querySelectorAll('style');
        styles.forEach(style => {
            let css = style.innerHTML;
            // This regex removes @import rules that trigger security errors
            style.innerHTML = css.replace(/@import url$$['"]?https?:\/\/fonts\.googleapis\.com\/css.*?['"]?$$;/g, '');
        });

        // 3. Serialize to XML
        const serializer = new XMLSerializer();
        const svgData = serializer.serializeToString(svgClone);

        // 4. Setup Canvas
        const canvas = document.createElement("canvas");
        const ctx = canvas.getContext("2d");
        const svgSize = originalSvg.getBoundingClientRect();
        
        // Use 2x scale for high resolution
        const scale = 2;
        canvas.width = svgSize.width * scale;
        canvas.height = svgSize.height * scale;

        const img = new Image();
        
        // Use Base64 encoding - this is more "trusted" by the canvas than a Blob URL
        const svgBase64 = btoa(unescape(encodeURIComponent(svgData)));
        img.src = "data:image/svg+xml;base64," + svgBase64;

        img.onload = function() {
            // Fill background white
            ctx.fillStyle = "white";
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            // Draw image at scaled size
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
            
            try {
                // Try to export as PNG
                const pngUrl = canvas.toDataURL("image/png");
                const downloadLink = document.createElement("a");
                downloadLink.href = pngUrl;
                downloadLink.download = `Project_Export_${Date.now()}.png`;
                downloadLink.click();
            } catch (e) {
                console.warn("Canvas still tainted, falling back to SVG export.");
                downloadAsSVG(svgData);
            }
        };

    } catch (err) {
        console.error("Export Error:", err);
        alert("Export failed. Try right-clicking the chart and 'Save Image As'.");
    }
};

// --- 🛡️ FAIL-SAFE: DOWNLOAD AS SVG ---
function downloadAsSVG(svgData) {
    const blob = new Blob([svgData], { type: "image/svg+xml;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `Project_Export_${Date.now()}.svg`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

async function confirmTaskToSheet(taskData, btn) {
    btn.disabled = true;
    btn.innerHTML = "⌛ Adding...";

    try {
        // FIXED: Corrected the opening of the fetch call
        const response = await fetch(`${API_BASE_URL}/tasks`, { 
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(taskData)
        });

        const result = await response.json();
        
        if (response.ok) {
            // Find the parent card and show success
            const card = btn.closest('.task-preview-card');
            if (card) {
                card.innerHTML = `
                    <div style="color: #059669; font-weight: bold; padding: 10px; text-align: center; background: #ecfdf5; border-radius: 8px;">
                        ✅ ${result.message || "Task added to Google Sheets!"} ✨
                    </div>`;
            }
        } else {
            // Handle server-side errors (like the connection error we discussed)
            alert("Error: " + (result.detail || "Failed to add task to sheets. Check Railway logs."));
            btn.disabled = false;
            btn.innerHTML = "Confirm & Add";
        }
    } catch (err) {
        console.error("Save failed", err);
        alert("Failed to connect to your Railway server. Please check your internet or if the service is awake.");
        btn.disabled = false;
        btn.innerHTML = "Confirm & Add";
    }
}


// 🌐 GLOBAL FUNCTIONS (for onclick handlers)
window.checkHealth = checkHealth;
window.getSummary = getSummary;
window.loadAllTasks = loadAllTasks;
window.searchTasks = searchTasks;
window.sendChat = sendChat;
window.updateTaskStatus = updateTaskStatus;
window.clearTasksList = clearTasksList;
window.downloadTasksCSV = downloadTasksCSV;
window.downloadSummary = downloadSummary;
window.renderStatusChart = renderStatusChart;
window.renderResourceChart = renderResourceChart;
window.toggleChatVoice = toggleChatVoice;
window.loadVisualization = loadVisualization;
window.generateGantt = generateGantt;
window.generateFlowchart = generateFlowchart;
window.populateClientDropdown = populateClientDropdown;
//document.addEventListener('DOMContentLoaded', () => {loadAllTasks()});
// --- 🚀 PAGE INITIALIZATION ---
document.addEventListener('DOMContentLoaded', () => {
    console.log("Page loaded. Initializing systems...");

    // 1. Always check API Health (Exists on both pages)
    if (typeof checkAPIHealth === 'function') {
        checkAPIHealth();
    }

    // 2. Load Data (This fetches tasks and then updates UI/Charts safely)
    loadAllTasks();

    // 3. Initialize Mermaid (Only if we are on the Dashboard/Index)
    if (window.mermaid && document.getElementById('mermaid-container')) {
        mermaid.initialize({ startOnLoad: true });
    }
});

