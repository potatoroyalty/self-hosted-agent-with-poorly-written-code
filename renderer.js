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
    const pauseBtn = document.getElementById('pause-btn');
    const stopBtn = document.getElementById('stop-btn');
    const scriptSelector = document.getElementById('script-selector');

    socket.on('script_list', (data) => {
        const scripts = data.scripts || [];
        // Clear existing options except the first one
        scriptSelector.innerHTML = '<option value="">Select a script...</option>';
        scripts.forEach(script => {
            const option = document.createElement('option');
            option.value = script;
            option.textContent = script;
            scriptSelector.appendChild(option);
        });
    });

    scriptSelector.addEventListener('change', () => {
        const selectedScript = scriptSelector.value;
        if (selectedScript) {
            console.log(`Selected script: ${selectedScript}`);
            socket.emit('run_script', { script: selectedScript });
            // Optionally, show loading overlay as running a script is like starting the agent
            loadingOverlay.style.display = 'flex';
            // Reset selector to default after running
            scriptSelector.value = "";
        }
    });

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

    pauseBtn.addEventListener('click', () => {
        console.log('Pause button clicked.');
        socket.emit('pause_agent');
    });

    stopBtn.addEventListener('click', () => {
        console.log('Stop button clicked.');
        socket.emit('stop_agent');
        loadingOverlay.style.display = 'none';
    });

    const recordBtn = document.getElementById('record-btn');
    const recordingBanner = document.getElementById('recording-banner');
    let isRecording = false;

    recordBtn.addEventListener('click', () => {
        isRecording = !isRecording; // Toggle recording state

        if (isRecording) {
            // Start recording
            recordBtn.textContent = 'Stop Recording';
            recordBtn.classList.add('recording');
            recordingBanner.style.display = 'block';
            socket.emit('start_recording');
            console.log('Started recording.');
        } else {
            // Stop recording
            recordBtn.textContent = 'Record New Script';
            recordBtn.classList.remove('recording');
            recordingBanner.style.display = 'none';
            socket.emit('stop_recording');
            console.log('Stopped recording.');
        }
    });

    socket.on('agent_finished', (data) => {
        console.log('Agent has finished its task.', data);
        loadingOverlay.style.display = 'none';
    });

    socket.on('status_update', (data) => {
        document.querySelector('.status-bar span:nth-child(1)').textContent = `Status: ${data.status}`;
        document.querySelector('.status-bar span:nth-child(2)').textContent = `IP: ${data.ip}`;
        document.querySelector('.status-bar span:nth-child(3)').textContent = `User-Agent: ${data.user_agent}`;
        document.querySelector('.status-bar span:nth-child(4)').textContent = `Speed: ${data.speed}`;
        document.querySelector('.status-bar span:nth-child(5)').textContent = `Stealth: ${data.stealth}`;
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

    // --- Quick Toggles Logic ---
    const toggles = document.querySelectorAll('.quick-toggles input[type="checkbox"]');
    toggles.forEach(toggle => {
        // We don't want to add a listener to the theme-toggle here, as it has its own script.
        if (toggle.id !== 'theme-toggle') {
            toggle.addEventListener('change', (e) => {
                const configKey = e.target.id;
                const configValue = e.target.checked;
                console.log(`Toggle changed: ${configKey}, New value: ${configValue}`);
                socket.emit('update_config', { key: configKey, value: configValue });
            });
        }
    });

    // --- Generator View Logic ---
    const generateScriptBtn = document.getElementById('generate-script-btn');
    generateScriptBtn.addEventListener('click', () => {
        console.log('Generate Script button clicked.');
        // In a real implementation, this would trigger a call to the backend
        // to generate a script based on recorded actions or other inputs.
        alert('Script generation is not fully implemented yet.');
    });

    // --- Browser Control Logic ---
    const browserIframe = document.getElementById('browser-iframe');
    const urlBar = document.getElementById('url-bar');
    const backBtn = document.getElementById('back-btn');
    const forwardBtn = document.getElementById('forward-btn');
    const refreshBtn = document.getElementById('refresh-btn');

    // Function to navigate the iframe
    function navigateTo(url) {
        // A simple check to prepend https:// if no protocol is present
        if (!/^(https?:\/\/|about:)/.test(url)) {
            url = 'https://' + url;
        }
        browserIframe.src = url;
    }

    // Event listener for the URL bar
    urlBar.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            navigateTo(urlBar.value);
        }
    });

    // Event listeners for navigation buttons
    backBtn.addEventListener('click', () => {
        browserIframe.contentWindow.history.back();
    });

    forwardBtn.addEventListener('click', () => {
        browserIframe.contentWindow.history.forward();
    });

    refreshBtn.addEventListener('click', () => {
        browserIframe.contentWindow.location.reload();
    });

    // Update URL bar and inject bridge script when iframe navigation changes
    browserIframe.addEventListener('load', () => {
        try {
            const newLocation = browserIframe.contentWindow.location.href;

            // Update the URL bar
            if (newLocation !== 'about:blank') {
                urlBar.value = newLocation;
            }

            // Inject the bridge script
            fetch('/bridge.js')
                .then(response => {
                    if (!response.ok) {
                        throw new Error('Failed to fetch bridge.js');
                    }
                    return response.text();
                })
                .then(scriptText => {
                    const script = browserIframe.contentDocument.createElement('script');
                    script.textContent = scriptText;
                    browserIframe.contentDocument.head.appendChild(script);
                    console.log('Successfully injected bridge.js into iframe.');
                })
                .catch(err => {
                    console.error('Error injecting bridge.js:', err);
                });

        } catch (e) {
            // This can happen due to cross-origin restrictions.
            console.warn("Could not access iframe location or inject script due to cross-origin policy.", e.message);
        }
    });
});
