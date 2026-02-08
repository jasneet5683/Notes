// ✅ Corrected API configuration
const API_BASE_URL = 'https://web-production-b8ca4.up.railway.app';

// 📥 Load all tasks from backend
async function loadTasks() {
    console.log('🔄 Fetching tasks from Railway backend...');
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/tasks`);
        
        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        
        const tasks = await response.json();
        console.log('✅ Tasks received:', tasks);
        displayTasks(tasks);
        
    } catch (error) {
        console.error('❌ Failed to load tasks:', error);
        displayError('Unable to connect to backend. Check if Railway is running.');
    }
}

// 📊 Render tasks in UI with correct field mapping
function displayTasks(tasks) {
    const container = document.getElementById('tasks-container');
    
    if (!container) {
        console.error('❌ Element "tasks-container" not found in HTML');
        return;
    }
    
    if (!tasks || tasks.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #999; padding: 40px;">📭 No tasks yet</p>';
        return;
    }
    
    // Map backend fields to display names
    container.innerHTML = tasks.map(task => `
        <div class="task-card" style="
            background: linear-gradient(135deg, #f5f7ff 0%, #f0f4ff 100%);
            border: 1px solid #d4dce9;
            border-radius: 12px;
            padding: 20px;
            margin: 15px 0;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        ">
            <h3 style="margin: 0 0 15px 0; color: #1a202c;">📋 ${task.task_name || 'Unnamed'}</h3>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; font-size: 14px;">
                <div>
                    <strong style="color: #64748b;">👤 Assigned To</strong><br>
                    <span style="color: #334155;">${task.assigned_to || '—'}</span>
                </div>
                
                <div>
                    <strong style="color: #64748b;">🏢 Client</strong><br>
                    <span style="color: #334155;">${task.client || '—'}</span>
                </div>
                
                <div>
                    <strong style="color: #64748b;">📅 Start Date</strong><br>
                    <span style="color: #334155;">${task.start_date || '—'}</span>
                </div>
                
                <div>
                    <strong style="color: #64748b;">📍 Status</strong><br>
                    <span style="
                        display: inline-block;
                        background: ${getStatusColor(task.status)};
                        color: white;
                        padding: 4px 12px;
                        border-radius: 20px;
                        font-size: 12px;
                        font-weight: 600;
                    ">${task.status || 'Pending'}</span>
                </div>
            </div>
        </div>
    `).join('');
}

// 🎨 Color coding for status
function getStatusColor(status) {
    const colors = {
        'Completed': '#10b981',
        'In Progress': '#f59e0b',
        'Pending': '#6366f1',
        'On Hold': '#ef4444'
    };
    return colors[status] || '#6b7280';
}

// ➕ Add new task
async function addNewTask(event) {
    event.preventDefault();
    
    // Get form values
    const taskName = document.getElementById('taskName')?.value;
    const assignedTo = document.getElementById('assignedTo')?.value;
    const client = document.getElementById('client')?.value;
    const startDate = document.getElementById('startDate')?.value;
    const endDate = document.getElementById('endDate')?.value;
    const status = document.getElementById('status')?.value || 'Pending';
    
    // Validate required fields
    if (!taskName || !assignedTo) {
        displayError('Task Name and Assigned To are required');
        return;
    }
    
    console.log('📤 Submitting task:', { taskName, assignedTo, client, startDate, endDate, status });
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/add-task`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                task_name: taskName,        // ✅ Matches backend field
                assigned_to: assignedTo,    // ✅ Matches backend field
                client: client,             // ✅ Matches backend field
                start_date: startDate,      // ✅ Matches backend field
                end_date: endDate,
                status: status
            })
        });
        
        if (!response.ok) {
            throw new Error(`Failed to add task: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('✅ Task added:', result);
        
        // Clear form
        document.querySelector('form')?.reset();
        
        // Reload tasks
        await loadTasks();
        displaySuccess('✅ Task added successfully!');
        
    } catch (error) {
        console.error('❌ Error adding task:', error);
        displayError('Failed to add task. Check backend connection.');
    }
}

// 🚨 Show error message
function displayError(message) {
    const container = document.getElementById('tasks-container');
    if (container) {
        container.innerHTML = `
            <div style="
                background: #fee2e2;
                color: #dc2626;
                padding: 20px;
                border-radius: 8px;
                border-left: 4px solid #dc2626;
            ">
                ❌ ${message}
            </div>
        `;
    }
}

// ✅ Show success message
function displaySuccess(message) {
    const container = document.getElementById('tasks-container');
    if (container) {
        const alert = document.createElement('div');
        alert.style.cssText = `
            background: #dcfce7;
            color: #16a34a;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #16a34a;
        `;
        alert.textContent = message;
        container.insertAdjacentElement('beforebegin', alert);
        
        setTimeout(() => alert.remove(), 3000);
    }
}

// 🚀 Auto-load tasks when page opens
document.addEventListener('DOMContentLoaded', () => {
    console.log('🌐 Page loaded, fetching tasks...');
    loadTasks();
    
    // Attach form handler if exists
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', addNewTask);
    }
});
