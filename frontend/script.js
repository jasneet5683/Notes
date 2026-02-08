// script.js - Load and display tasks from backend API

async function loadTasks() {
    try {
        // Fetch tasks from your backend API
        const response = await fetch('/api/tasks');
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const tasks = await response.json();
        console.log('Tasks loaded:', tasks);
        
        displayTasks(tasks);
    } catch (error) {
        console.error('Error loading tasks:', error);
        document.getElementById('tasksContainer').innerHTML = 
            '<p style="color: red;">Failed to load tasks. Check console.</p>';
    }
}

function displayTasks(tasks) {
    const container = document.getElementById('tasksContainer');
    
    // Handle empty results
    if (!tasks || tasks.length === 0) {
        container.innerHTML = '<p>No tasks available</p>';
        return;
    }
    
    // Render each task as a card
    container.innerHTML = tasks.map(task => `
        <div class="task-card" style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 8px;">
            <h3>${task['Task Name'] || 'Unnamed Task'}</h3>
            <p><strong>Assigned to:</strong> ${task.assigned_to || 'Unassigned'}</p>
            <p><strong>Client:</strong> ${task.Client || 'N/A'}</p>
            <p><strong>Duration:</strong> ${task.start_date} → ${task.end_date}</p>
            <p><strong>Status:</strong> <span style="background: #f0f0f0; padding: 4px 8px; border-radius: 4px;">${task.status || 'Unknown'}</span></p>
        </div>
    `).join('');
}

// Load tasks when page loads
document.addEventListener('DOMContentLoaded', loadTasks);
