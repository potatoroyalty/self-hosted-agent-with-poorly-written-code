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
        const sanitizedData = DOMPurify.sanitize(data.data);
        logContainer.innerHTML += `<p>${sanitizedData}</p>`;
    });

    socket.on('log_update', (data) => {
        const logContainer = document.getElementById('live-log');
        // Sanitize the data to prevent HTML injection using DOMPurify
        const sanitizedData = DOMPurify.sanitize(data.data);
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

    socket.on('browser_navigated', (data) => {
        const browserIframe = document.getElementById('browser-iframe');
        const urlBar = document.getElementById('url-bar');
        console.log(`[SOCKETS] Received 'browser_navigated' event. URL: ${data.url}`);
        if (browserIframe.src !== data.url) {
            browserIframe.src = data.url;
        }
        urlBar.value = data.url;
    });

    socket.on('agent_view_updated', (data) => {
        const overlay = document.getElementById('agent-view-overlay');
        const overlayImage = document.getElementById('agent-view-image');
        console.log('[SOCKETS] Received agent_view_updated event. Displaying annotated screenshot.');
        overlayImage.src = `data:image/png;base64,${data.image}`;
        overlay.style.display = 'flex';
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
        loadScripts();
    });

    async function loadScripts() {
        try {
            const response = await fetch('/get_scripts');
            if (!response.ok) {
                throw new Error('Failed to fetch scripts');
            }
            const data = await response.json();
            const scriptList = document.getElementById('script-list');
            scriptList.innerHTML = ''; // Clear existing list

            if (data.scripts && data.scripts.length > 0) {
                data.scripts.forEach(script => {
                    const li = document.createElement('li');
                    li.textContent = script;

                    const deleteButton = document.createElement('button');
                    deleteButton.textContent = 'Delete';
                    deleteButton.className = 'delete-btn';
                    deleteButton.onclick = () => deleteScript(script);

                    li.appendChild(deleteButton);
                    scriptList.appendChild(li);
                });
            } else {
                scriptList.innerHTML = '<li>No scripts found.</li>';
            }
        } catch (error) {
            console.error('Error loading scripts:', error);
            const scriptList = document.getElementById('script-list');
            scriptList.innerHTML = '<li>Error loading scripts.</li>';
        }
    }

    function deleteScript(scriptName) {
        if (confirm(`Are you sure you want to delete the script: ${scriptName}?`)) {
            socket.emit('delete_script', { script_name: scriptName });
        }
    }

    socket.on('script_deleted', (data) => {
        if (data.success) {
            alert(`Script '${data.script_name}' deleted successfully.`);
            loadScripts(); // Refresh the list
            socket.emit('request_script_list'); // Refresh the dropdown in browser view
        } else {
            alert(`Error deleting script: ${data.error}`);
        }
    });

    proxiesLink.addEventListener('click', (e) => {
        e.preventDefault();
        switchView(proxiesView, proxiesLink);
        loadProxies();
    });

    async function loadProxies() {
        try {
            const response = await fetch('/get_proxies');
            if (!response.ok) {
                throw new Error('Failed to fetch proxies');
            }
            const data = await response.json();
            const proxyTableBody = document.getElementById('proxy-table-body');
            proxyTableBody.innerHTML = ''; // Clear existing table

            if (data.proxies && data.proxies.length > 0) {
                data.proxies.forEach(proxy => {
                    addProxyRow(proxy.alias, proxy.address);
                });
            }
        } catch (error) {
            console.error('Error loading proxies:', error);
            const proxyTableBody = document.getElementById('proxy-table-body');
            proxyTableBody.innerHTML = '<tr><td colspan="3">Error loading proxies.</td></tr>';
        }
    }

    function addProxyRow(alias = '', address = '') {
        const proxyTableBody = document.getElementById('proxy-table-body');
        const row = document.createElement('tr');

        row.innerHTML = `
            <td><input type="text" class="proxy-alias" value="${alias}" placeholder="e.g., Home Proxy"></td>
            <td><input type="text" class="proxy-address" value="${address}" placeholder="e.g., http://user:pass@host:port"></td>
            <td><button class="delete-proxy-btn">Delete</button></td>
        `;

        row.querySelector('.delete-proxy-btn').addEventListener('click', () => {
            row.remove();
        });

        proxyTableBody.appendChild(row);
    }

    document.getElementById('add-proxy-btn').addEventListener('click', () => {
        addProxyRow();
    });

    document.getElementById('save-proxies-btn').addEventListener('click', () => {
        const proxyTableBody = document.getElementById('proxy-table-body');
        const rows = proxyTableBody.querySelectorAll('tr');
        const proxies = [];
        rows.forEach(row => {
            const alias = row.querySelector('.proxy-alias').value.trim();
            const address = row.querySelector('.proxy-address').value.trim();
            if (alias && address) {
                proxies.push({ alias, address });
            }
        });

        if (confirm(`Are you sure you want to save these ${proxies.length} proxies? This will overwrite the existing list.`)) {
            socket.emit('save_proxies', { proxies: proxies });
        }
    });

    socket.on('proxies_saved', (data) => {
        if (data.success) {
            alert('Proxies saved successfully!');
            loadProxies(); // Refresh the list
        } else {
            alert(`Error saving proxies: ${data.error}`);
        }
    });

    async function fetchLog(logType, elementId) {
        const element = document.getElementById(elementId);
        element.textContent = 'Loading...'; // Show loading indicator
        try {
            const response = await fetch(`/get_log_content/${logType}`);
            if (!response.ok) {
                throw new Error(`Failed to fetch ${logType} log: ${response.statusText}`);
            }
            const data = await response.json();
            if (data.error) {
                throw new Error(data.error);
            }
            element.textContent = data.content || '(empty)';
        } catch (error) {
            console.error(`Error loading ${logType} log:`, error);
            element.textContent = `Error loading log: ${error.message}`;
        }
    }

    function clearLog(logType) {
        if (confirm(`Are you sure you want to clear the ${logType} log? This action cannot be undone.`)) {
            socket.emit('clear_log', { log_type: logType });
        }
    }

    socket.on('log_cleared', (data) => {
        if (data.success) {
            alert(`${data.log_type} log cleared successfully.`);
            // Refresh the view
            fetchLog(data.log_type, `${data.log_type}-log-content`);
        } else {
            alert(`Error clearing log: ${data.error}`);
        }
    });


    logsLink.addEventListener('click', (e) => {
        e.preventDefault();
        switchView(logsView, logsLink);
        fetchLog('critique', 'critique-log-content');
        fetchLog('memory', 'memory-log-content');
    });

    document.getElementById('refresh-critique-log').addEventListener('click', () => fetchLog('critique', 'critique-log-content'));
    document.getElementById('clear-critique-log').addEventListener('click', () => clearLog('critique'));
    document.getElementById('refresh-memory-log').addEventListener('click', () => fetchLog('memory', 'memory-log-content'));
    document.getElementById('clear-memory-log').addEventListener('click', () => clearLog('memory'));

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
    const scriptNameInput = document.getElementById('script-name-input');
    const scriptObjectiveInput = document.getElementById('script-objective-input');
    const scriptEditor = document.getElementById('script-editor');

    generateScriptBtn.addEventListener('click', () => {
        const scriptName = scriptNameInput.value.trim();
        const objective = scriptObjectiveInput.value.trim();

        if (!scriptName || !objective) {
            alert('Please provide both a script name and an objective.');
            return;
        }

        console.log(`Requesting script generation for name: '${scriptName}' and objective: '${objective}'`);
        // Show a loading message in the editor
        scriptEditor.innerHTML = '<p>Generating script... Please wait.</p>';

        socket.emit('generate_script', {
            script_name: scriptName,
            objective: objective
        });
    });

    socket.on('script_generated', (data) => {
        console.log('Received generated script from server.');
        if (data.success) {
            // Display the generated script in the editor
            // We'll use a simple <pre> tag to preserve formatting.
            // A more advanced implementation would use a real code editor library like CodeMirror or Monaco.
            const pre = document.createElement('pre');
            const code = document.createElement('code');
            code.textContent = data.script_content;
            pre.appendChild(code);
            scriptEditor.innerHTML = ''; // Clear previous content
            scriptEditor.appendChild(pre);

            // Notify the user
            alert(`Script '${data.script_name}' generated successfully!`);

            // Refresh the script list in the Browser view
            socket.emit('request_script_list');

        } else {
            scriptEditor.innerHTML = `<p class="error">Error generating script: ${data.error}</p>`;
            alert(`Error generating script: ${data.error}`);
        }
    });

    socket.on('request_script_list', () => {
        // This is a simple way to trigger a refresh of the script list.
        // The server should handle the 'request_script_list' event and send back a 'script_list' event.
         console.log('Requesting updated script list from server.');
    });

    // --- Browser Control Logic ---
    const agentViewOverlay = document.getElementById('agent-view-overlay');
    agentViewOverlay.addEventListener('click', () => {
        agentViewOverlay.style.display = 'none'; // Hide on click
    });

    socket.on('action_executed', (data) => {
        const overlay = document.getElementById('agent-view-overlay');
        if (overlay.style.display === 'flex' && data.box) {
            const overlayImg = document.getElementById('agent-view-image');
            if (!overlayImg.naturalWidth) {
                // Image hasn't loaded yet, can't calculate scale.
                return;
            }

            console.log(`[SOCKETS] Highlighting action '${data.action}' at`, data.box);

            const highlight = document.createElement('div');
            highlight.className = 'action-highlight';

            const imgRect = overlayImg.getBoundingClientRect();
            const overlayRect = overlay.getBoundingClientRect();

            const scaleX = imgRect.width / overlayImg.naturalWidth;
            const scaleY = imgRect.height / overlayImg.naturalHeight;
            const scale = Math.min(scaleX, scaleY);

            const imgX = imgRect.left - overlayRect.left + (imgRect.width - (overlayImg.naturalWidth * scale)) / 2;
            const imgY = imgRect.top - overlayRect.top + (imgRect.height - (overlayImg.naturalHeight * scale)) / 2;

            highlight.style.left = `${(data.box.x * scale) + imgX}px`;
            highlight.style.top = `${(data.box.y * scale) + imgY}px`;
            highlight.style.width = `${data.box.width * scale}px`;
            highlight.style.height = `${data.box.height * scale}px`;

            if (data.action === 'type') {
                highlight.style.backgroundColor = 'rgba(144, 238, 144, 0.4)';
                highlight.style.borderColor = '#90EE90';
            }

            overlay.appendChild(highlight);

            setTimeout(() => {
                highlight.remove();
            }, 1500);
        }
    });

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

    // --- Settings Page Logic ---
    const settingsForm = document.getElementById('settings-form');

    function populateSettingsForm(settings) {
        for (const key in settings) {
            const input = settingsForm.elements[key];
            if (input) {
                if (input.type === 'checkbox') {
                    input.checked = settings[key];
                } else {
                    input.value = settings[key];
                }
            }
        }
    }

    async function loadSettings() {
        try {
            const response = await fetch('/get_settings');
            if (!response.ok) {
                throw new Error('Failed to fetch settings');
            }
            const settings = await response.json();
            populateSettingsForm(settings);

            // Automatically load the start URL in the browser view
            if (settings.START_URL) {
                navigateTo(settings.START_URL);
            }
        } catch (error) {
            console.error('Error loading settings:', error);
            // Optionally, show an error message to the user
        }
    }

    function handleSettingChange(e) {
        const input = e.target;
        const key = input.name;
        let value;

        if (input.type === 'checkbox') {
            value = input.checked;
        } else if (input.type === 'number' || input.type === 'range') {
            value = parseFloat(input.value);
        } else {
            value = input.value;
        }

        console.log(`Setting changed: ${key}, New value: ${value}`);
        socket.emit('update_config', { key: key, value: value });
    }

    // Add event listeners to all form elements in the settings form
    if (settingsForm) {
        Array.from(settingsForm.elements).forEach(element => {
            element.addEventListener('change', handleSettingChange);
        });
    }

    // Load settings when the DOM is ready
    loadSettings();

    // --- Settings Page Save Button ---
    const saveSettingsBtn = document.getElementById('save-settings-btn');
    if (saveSettingsBtn) {
        saveSettingsBtn.addEventListener('click', () => {
            // The settings are already saved on change, so this is just for UX.
            // We can give a visual confirmation.
            saveSettingsBtn.textContent = 'Saved!';
            saveSettingsBtn.style.backgroundColor = '#2ecc71'; // Green
            setTimeout(() => {
                saveSettingsBtn.textContent = 'Save Settings';
                saveSettingsBtn.style.backgroundColor = ''; // Revert to default
            }, 2000);
        });
    }
});
