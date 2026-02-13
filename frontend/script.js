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
    try {
        const summaryDisplay = document.getElementById('summaryDisplay');
        
        // 1. Check local data
        if (!allTasksData || allTasksData.length === 0) {
            summaryDisplay.innerHTML = '<div class="error">⚠️ No tasks found. Please Refresh Data.</div>';
            return;
        }

        summaryDisplay.innerHTML = '<div class="loading">📊 Analyzing priorities, deadlines & workload...</div>';

        // 2. Calculate Hard Facts (To prevent counting errors)
        const total = allTasksData.length;
        const pending = allTasksData.filter(t => (t.status||'').toLowerCase().includes('pending')).length;
        const progress = allTasksData.filter(t => (t.status||'').toLowerCase().includes('progress')).length;
        const completed = allTasksData.filter(t => (t.status||'').toLowerCase().includes('completed')).length;
        const hold = allTasksData.filter(t => (t.status||'').toLowerCase().includes('hold')).length;
        const cancelled = allTasksData.filter(t => (t.status||'').toLowerCase().includes('cancelled')).length;

        // 3. Prepare FULL Data for AI
        // We map the raw data to a cleaner object to save tokens but keep all info
        const detailedTasks = allTasksData.map(t => ({
            task: t.Task_Name,
            status: t.status,
            assignee: t.assigned_to || "Unassigned",
            priority: t.Priority || "N/A",
            start: t.start_date || "N/A",
            due: t.end_date || "N/A",
            client: t.Client || "General"
        }));

        // 4. Construct the Prompt
        const prompt = `
            I need a professional Project Status Report.
            
            HARD DATA SUMMARY (Use these numbers as absolute truth):
            - Total Tasks: ${total}
            - Pending: ${pending} 
            - In Progress: ${progress}
            - Completed: ${completed}
            - On Hold: ${hold}
            - Cancelled: ${cancelled}
            - Today's Date: ${new Date().toLocaleDateString()}

            DETAILED TASK LIST (JSON):
            ${JSON.stringify(detailedTasks)}

            INSTRUCTIONS:
            Based on the data above, write a concise summary (max 150 words) covering:
            1. 🚩 **Blockers & Risks**: Are there high-priority tasks pending? Any overdue dates?
            2. 👥 **Workload**: Who is assigned the most work?
            3. 📈 **Progress**: General health of the project.
            
            Use bullet points and bold text for key insights.
        `;

        // 5. Send to Backend
        const response = await fetch(`${API_BASE_URL}/ask`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: prompt })
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        const aiText = data.answer || data.response;

        // 6. Render Output
        // Use 'marked.parse(aiText)' if you have the marked.js library, otherwise just use aiText
        // We wrap it in a nice container with the hard stats visible at top
        summaryDisplay.innerHTML = 
            `<div class="summary-box">
                <h3>🧠 Smart Project Analysis</h3>
                <div class="stats-bar" style="display:flex; gap:15px; margin-bottom:15px; padding-bottom:10px; border-bottom:1px solid #eee; font-size:0.9rem;">
                    <span><b>Total:</b> ${total}</span>
                    <span style="color:#e67e22"><b>Pending:</b> ${pending}</span>
                    <span style="color:#17a2b8"><b>In Progress:</b> ${progress}</span>
                    <span style="color:#28a745"><b>Done:</b> ${completed}</span>
                    <span style="color:#818589"><b>On Hold:</b> ${hold}</span>
                    <span style="color:#dc143c"><b>Cancelled:</b> ${cancelled}</span>
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
        document.getElementById('summaryDisplay').innerHTML = 
            `<div class="error">❌ Analysis Failed: ${error.message}</div>`;
    }
}

// 📋 3. GET ALL TASKS
async function loadAllTasks() {
    try {
        document.getElementById('taskList').innerHTML = '<div class="loading">🔄 Loading all tasks...</div>';
        
        const response = await fetch(`${API_BASE_URL}/tasks`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const data = await response.json();
        allTasksData = data.tasks || []; 
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
        priority: String(document.getElementById('priority').value || "1"),
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

    // Regex to find: ```chart ... ```
    const chartRegex = /```chart\s*([\s\S]*?)\s*```/;
    const match = content.match(chartRegex);

    if (match) {
        // --- CASE A: CHART DETECTED ---
        
        // 1. Render text before the chart
        const textBefore = content.split("```chart")[0];
        msgDiv.innerHTML = marked.parse(textBefore);

        // 2. Create Chart Container
        const canvasId = "chart-" + Date.now();
        const chartContainer = document.createElement("div");
        chartContainer.className = "chart-wrapper"; 
        chartContainer.innerHTML = `<canvas id="${canvasId}"></canvas>`;
        msgDiv.appendChild(chartContainer);
        
        container.appendChild(msgDiv);

        // 3. Process & Draw Chart
        try {
            let chartData = JSON.parse(match[1]);

            // 🔥 MAGIC: Apply Dynamic Colors before drawing
            chartData = smartColorize(chartData);

            const ctx = document.getElementById(canvasId).getContext('2d');
            new Chart(ctx, chartData);

        } catch (e) {
            console.error("Chart Render Error:", e);
            msgDiv.insertAdjacentHTML('beforeend', "<p style='color:red; font-size:small'>❌ Error loading chart.</p>");
        }
    } else {
        // --- CASE B: STANDARD TEXT ---
        msgDiv.innerHTML = marked.parse(content);
        container.appendChild(msgDiv);
    }

    // Scroll to bottom
    container.scrollTop = container.scrollHeight;
}

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
    switch(priority) {
        case 1: return '🟢'; // Low
        case 2: return '🟡'; // Medium  
        case 3: return '🟠'; // High
        case 4: return '🔴'; // Critical
        default: return '⚪'; // Unknown
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
    if (typeof allTasksData === 'undefined' || !allTasksData || allTasksData.length === 0) {
        alert("⚠️ No data found! Please click 'Refresh Data' first.");
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
    if (!allTasksData || allTasksData.length === 0) {
        alert("No data available. Please refresh.");
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

