// Handles tab switching in the right sidebar
function openTab(evt, tabName) {
    // Get all elements with class="tab-content" and hide them
    let tabcontent = document.getElementsByClassName("tab-content");
    for (let i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = "none";
    }

    // Get all elements with class="tab-link" and remove the class "active"
    let tablinks = document.getElementsByClassName("tab-link");
    for (let i = 0; i < tablinks.length; i++) {
        tablinks[i].className = tablinks[i].className.replace(" active", "");
    }

    // Show the current tab, and add an "active" class to the button that opened the tab
    document.getElementById(tabName).style.display = "block";
    evt.currentTarget.className += " active";
}

// Handles view switching in the main content area
document.addEventListener('DOMContentLoaded', () => {
    const socket = io();
    const loadingOverlay = document.getElementById('loading-overlay');

    socket.on('connect', () => {
        console.log('Connected to WebSocket server!');
    });

    socket.on('response', (data) => {
        console.log('Message from server:', data);
        const logContainer = document.getElementById('live-log');
        logContainer.innerHTML += `<p>${data.data}</p>`;
    });

    socket.on('log_update', (data) => {
        const logContainer = document.getElementById('live-log');
        // Sanitize the data to prevent HTML injection
        const sanitizedData = data.data.replace(/</g, "&lt;").replace(/>/g, "&gt;");
        logContainer.innerHTML += `<p>${sanitizedData}</p>`;
        // Scroll to the bottom of the log
        logContainer.scrollTop = logContainer.scrollHeight;
    });

    socket.on('clarification_request', (data) => {
        console.log('Clarification request from agent:', data);
        // If we get a clarification request, the agent is clearly not "done"
        loadingOverlay.style.display = 'none';
        const container = document.getElementById('clarification-container');

        // Clear previous content
        container.innerHTML = '<h3>Agent needs your help!</h3>';

        // Display the world model
        const worldModel = document.createElement('p');
        worldModel.textContent = data.world_model;
        container.appendChild(worldModel);

        // Display the potential actions as buttons
        const actionList = document.createElement('ul');
        data.potential_actions.forEach(action => {
            const actionItem = document.createElement('li');
            const actionButton = document.createElement('button');
            actionButton.textContent = action;
            actionButton.addEventListener('click', () => {
                socket.emit('clarification_response', {
                    request_id: data.request_id,
                    selected_action: action
                });
                // Hide the container after selection
                container.style.display = 'none';
                container.innerHTML = '';
            });
            actionItem.appendChild(actionButton);
            actionList.appendChild(actionItem);
        });
        container.appendChild(actionList);

        // Show the container
        container.style.display = 'block';
    });

    const startBtn = document.getElementById('start-btn');
    startBtn.addEventListener('click', () => {
        const objective = document.getElementById('instruction-input').value;
        if (objective) {
            console.log('Start button clicked with objective:', objective);
            loadingOverlay.style.display = 'flex';
            socket.emit('start_agent', { objective: objective });
        } else {
            alert("Please enter an objective.");
        }
    });

    socket.on('agent_finished', (data) => {
        console.log('Agent has finished its task.', data);
        loadingOverlay.style.display = 'none';
    });

    const views = document.querySelectorAll('.view');
    const navLinks = document.querySelectorAll('.nav-link');

    const browserLink = document.getElementById('view-browser-link');
    const generatorLink = document.getElementById('view-generator-link');
    const scriptsLink = document.getElementById('view-scripts-link');
    const proxiesLink = document.getElementById('view-proxies-link');
    const logsLink = document.getElementById('view-logs-link');
    const settingsLink = document.getElementById('view-settings-link');

    const browserView = document.getElementById('browser-view');
    const generatorView = document.getElementById('generator-view');
    const scriptsView = document.getElementById('scripts-view');
    const proxiesView = document.getElementById('proxies-view');
    const logsView = document.getElementById('logs-view');
    const settingsView = document.getElementById('settings-view');

    function switchView(viewToShow, activeLink) {
        // Hide all views
        views.forEach(view => {
            view.style.display = 'none';
        });

        // Show the target view
        if (viewToShow) {
            // #browser-view and #generator-view are flex containers.
            viewToShow.style.display = (viewToShow.id === 'browser-view' || viewToShow.id === 'generator-view') ? 'flex' : 'block';
        }

        // Update active class on nav links
        navLinks.forEach(link => {
            link.classList.remove('active');
        });
        if (activeLink) {
            activeLink.classList.add('active');
        }
    }

    // Add event listeners
    browserLink.addEventListener('click', (e) => {
        e.preventDefault();
        switchView(browserView, browserLink);
    });

    generatorLink.addEventListener('click', (e) => {
        e.preventDefault();
        switchView(generatorView, generatorLink);
    });

    scriptsLink.addEventListener('click', (e) => {
        e.preventDefault();
        switchView(scriptsView, scriptsLink);
    });

    proxiesLink.addEventListener('click', (e) => {
        e.preventDefault();
        switchView(proxiesView, proxiesLink);
    });

    logsLink.addEventListener('click', (e) => {
        e.preventDefault();
        switchView(logsView, logsLink);
    });

    settingsLink.addEventListener('click', (e) => {
        e.preventDefault();
        switchView(settingsView, settingsLink);
    });

    // Set the initial view
    switchView(browserView, browserLink);
});
