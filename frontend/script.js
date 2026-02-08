// script.js - Production Ready

async function loadTasks() {
    console.log('🔄 Loading tasks from backend...');
    
    // ✅ Your actual Railway backend URL
    const API_URL = 'https://notes-production-7134.up.railway.app/api/tasks';
    
    try {
        const response = await fetch(API_URL);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const tasks = await response.json();
        console.log('✅ Tasks retrieved:', tasks);
        displayTasks(tasks);
        
    } catch (error) {
        console.error('❌ Error loading tasks:', error.message);
        
        // ✅ Safety check before DOM manipulation
        const container = document.getElementById('tasks-container');
        if (container) {
            container.innerHTML = `
                <div style="text-align: center; color: #ff6b6b; padding: 20px; background: #ffe8e8; border-radius: 8px;">
                    <p>❌ Failed to load tasks</p>
                    <small>Backend may be offline. Check console for details.</small>
                </div>
            `;
        }
    }
}

function displayTasks(tasks) {
    const container = document.getElementById('tasks-container');
    
    // ✅ Prevent null reference errors
    if (!container) {
        console.error('❌ Element #tasks-container not found in HTML');
        return;
    }
    
    // Handle empty state
    if (!tasks || tasks.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: #999; padding: 40px;">📭 No tasks available</p>';
        return;
    }
    
    // ✅ Render task cards with proper data binding
    container.innerHTML = tasks.map(task => `
        <div class="task-card" style="
            background: #f8f9ff; 
            border: 1px solid #e1e5e9; 
            border-radius: 12px; 
            padding: 20px; 
            margin: 15px 0; 
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        ">
            <h3 style="color: #2c3e50; margin: 0 0 12px 0;">
                📋 ${task['Task Name'] || 'Unnamed Task'}
            </h3>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px; font-size: 14px;">
                <div>
                    <strong style="color: #555;">👤 Assigned To:</strong>
                    <p style="margin: 4px 0; color: #34495e;">${task.assigned_to || 'Unassigned'}</p>
                </div>
                <div>
                    <strong style="color: #555;">🏢 Client:</strong>
                    <p style="margin: 4px 0; color: #34495e;">${task.Client || 'N/A'}</p>
                </div>
                <div>
                    <strong style="color: #555;">📅 Timeline:</strong>
                    <p style="margin: 4px 0; color: #7f8c8d;">${task.start_date || 'N/A'} → ${task.end_date || 'N/A'}</p>
                </div>
                <div>
                    <strong style="color: #555;">📊 Status:</strong>
                    <span style="background: #e8f5e8; color: #27ae60; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: bold;">
                        ${task.status || 'Unknown'}
                    </span>
                </div>
            </div>
        </div>
    `).join('');
    
    console.log(`✅ Rendered ${tasks.length} task(s)`);
}

// ✅ Wait for DOM to be ready before running
document.addEventListener('DOMContentLoaded', function() {
    console.log('📄 Page loaded, initializing task panel...');
    loadTasks();
    
    // Optional: Refresh tasks every 30 seconds
    setInterval(loadTasks, 30000);
});
