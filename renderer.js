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
    const agentStatusContainer = document.getElementById('agent-status-container');
    const agentStatusText = document.getElementById('agent-status-text');

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
        agentStatusContainer.style.display = 'none';
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

    // Initial state for buttons
    pauseBtn.disabled = true;
    stopBtn.disabled = true;

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

    function startAgent(objective, script = null) {
        if (objective) {
            console.log(`Starting agent with objective: ${objective}`);
            agentStatusText.textContent = 'Agent Running';
            agentStatusContainer.style.display = 'flex';
            startBtn.disabled = true;
            pauseBtn.disabled = false;
            stopBtn.disabled = false;

            // The backend will handle getting the script content
            const payload = script ? { script: script } : { objective: objective };
            const event = script ? 'run_script' : 'start_agent';
            socket.emit(event, payload);
        } else if (!script) {
             showNotification("Please enter an objective before starting.", "error");
        }
    }

    scriptSelector.addEventListener('change', () => {
        const selectedScript = scriptSelector.value;
        if (selectedScript) {
            console.log(`Selected script: ${selectedScript}`);
            startAgent(selectedScript, selectedScript);
            // Reset selector to default after running
            scriptSelector.value = "";
        }
    });

    startBtn.addEventListener('click', () => {
        const objective = document.getElementById('instruction-input').value;
        startAgent(objective);
    });

    pauseBtn.addEventListener('click', () => {
        const isPaused = pauseBtn.classList.toggle('paused');
        if (isPaused) {
            pauseBtn.textContent = 'Resume';
            agentStatusText.textContent = 'Agent Paused';
            console.log('Pause button clicked. Pausing agent.');
            socket.emit('pause_agent');
        } else {
            pauseBtn.textContent = 'Pause';
            agentStatusText.textContent = 'Agent Running';
            console.log('Resume button clicked. Resuming agent.');
            socket.emit('resume_agent');
        }
    });

    stopBtn.addEventListener('click', () => {
        console.log('Stop button clicked.');
        socket.emit('stop_agent');
        // The rest of the UI update logic is in the 'agent_finished' listener
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
        agentStatusContainer.style.display = 'none';
        startBtn.disabled = false;
        pauseBtn.disabled = true;
        stopBtn.disabled = true;
        pauseBtn.textContent = 'Pause';
        pauseBtn.classList.remove('paused');
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

    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingText = document.getElementById('loading-text');
    let currentView = null;

    function showLoading(text = 'Loading...') {
        loadingText.textContent = text;
        loadingOverlay.style.display = 'flex';
    }

    function hideLoading() {
        loadingOverlay.style.display = 'none';
    }

    const notificationContainer = document.getElementById('notification-container');

    function showNotification(message, type = 'info', duration = 5000) {
        const notif = document.createElement('div');
        notif.className = `notification ${type}`;
        notif.textContent = message;

        // Manually control fade-out for removal
        const fadeOutAnimation = `fadeOutNotification 0.5s ${duration / 1000 - 0.5}s forwards`;
        notif.style.animation = `slideIn 0.5s forwards, fadeOut 0.5s ${duration / 1000 - 0.5}s forwards`;


        notif.addEventListener('click', () => {
            notif.style.animation = 'fadeOutNotification 0.5s forwards';
            notif.addEventListener('animationend', () => {
                if (notificationContainer.contains(notif)) {
                    notificationContainer.removeChild(notif);
                }
            });
        });

        setTimeout(() => {
             if (notificationContainer.contains(notif)) {
                notificationContainer.removeChild(notif);
            }
        }, duration);

        notificationContainer.appendChild(notif);
    }

    function switchView(viewToShow, activeLink) {
        if (currentView === viewToShow) {
            return; // Don't do anything if it's the same view
        }

        // Hide current view
        if (currentView) {
            // Add a class to trigger fade-out animation
            currentView.classList.add('view-hidden');
            // Hide it after the animation
            setTimeout(() => {
                currentView.style.display = 'none';
                currentView.classList.remove('view-hidden');
            }, 500); // Must match animation duration
        }

        // Show the target view
        if (viewToShow) {
             // Remove any hiding classes
            viewToShow.classList.remove('view-hidden');
            // Set display style
            viewToShow.style.display = (viewToShow.id === 'browser-view' || viewToShow.id === 'generator-view' || viewToShow.id === 'proxies-view' || viewToShow.id === 'logs-view' || viewToShow.id === 'settings-view') ? 'flex' : 'block';
        }

        // Update active class on nav links
        navLinks.forEach(link => {
            link.classList.remove('active');
        });
        if (activeLink) {
            activeLink.classList.add('active');
        }
        currentView = viewToShow;
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
        showLoading('Loading scripts...');
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
        } finally {
            hideLoading();
        }
    }

    const confirmationModal = document.getElementById('confirmation-modal');
    const confirmationMessage = document.getElementById('confirmation-message');
    const confirmYesBtn = document.getElementById('confirm-yes-btn');
    const confirmNoBtn = document.getElementById('confirm-no-btn');

    function showConfirmation(message) {
        return new Promise((resolve) => {
            confirmationMessage.textContent = message;
            confirmationModal.style.display = 'flex';

            confirmYesBtn.onclick = () => {
                confirmationModal.style.display = 'none';
                resolve(true);
            };

            confirmNoBtn.onclick = () => {
                confirmationModal.style.display = 'none';
                resolve(false);
            };
        });
    }

    async function deleteScript(scriptName) {
        const confirmed = await showConfirmation(`Are you sure you want to delete the script: ${scriptName}?`);
        if (confirmed) {
            socket.emit('delete_script', { script_name: scriptName });
        }
    }

    socket.on('script_deleted', (data) => {
        if (data.success) {
            showNotification(`Script '${data.script_name}' deleted successfully.`, 'success');
            loadScripts(); // Refresh the list
            socket.emit('request_script_list'); // Refresh the dropdown in browser view
        } else {
            showNotification(`Error deleting script: ${data.error}`, 'error');
        }
    });

    proxiesLink.addEventListener('click', (e) => {
        e.preventDefault();
        switchView(proxiesView, proxiesLink);
        loadProxies();
    });

    async function loadProxies() {
        showLoading('Loading proxies...');
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
        } finally {
            hideLoading();
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

    document.getElementById('save-proxies-btn').addEventListener('click', async () => {
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

        const confirmed = await showConfirmation(`Are you sure you want to save these ${proxies.length} proxies? This will overwrite the existing list.`);
        if (confirmed) {
            socket.emit('save_proxies', { proxies: proxies });
        }
    });

    socket.on('proxies_saved', (data) => {
        if (data.success) {
            showNotification('Proxies saved successfully!', 'success');
            loadProxies(); // Refresh the list
        } else {
            showNotification(`Error saving proxies: ${data.error}`, 'error');
        }
    });

    async function fetchLog(logType, elementId) {
        const element = document.getElementById(elementId);
        showLoading(`Fetching ${logType} log...`);
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
        } finally {
            hideLoading();
        }
    }

    async function clearLog(logType) {
        const confirmed = await showConfirmation(`Are you sure you want to clear the ${logType} log? This action cannot be undone.`);
        if (confirmed) {
            socket.emit('clear_log', { log_type: logType });
        }
    }

    socket.on('log_cleared', (data) => {
        if (data.success) {
            showNotification(`${data.log_type} log cleared successfully.`, 'success');
            // Refresh the view
            fetchLog(data.log_type, `${data.log_type}-log-content`);
        } else {
            showNotification(`Error clearing log: ${data.error}`, 'error');
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
    // We need to set the currentView manually for the first time
    browserView.style.display = 'flex';
    currentView = browserView;


    // --- Quick Toggles Logic ---
    const quickToggles = [
        'stealth-mode',
        'proxy-usage',
        'load-images',
        'enable-js'
    ];

    quickToggles.forEach(toggleId => {
        const toggle = document.getElementById(toggleId);
        if (toggle) {
            toggle.addEventListener('change', (e) => {
                const configKey = toggleId;
                const configValue = e.target.checked;
                console.log(`Quick Toggle changed: ${configKey}, New value: ${configValue}`);
                socket.emit('update_config', { key: configKey, value: configValue });
            });
        } else {
            console.warn(`Quick toggle with ID '${toggleId}' not found.`);
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
            showNotification('Please provide both a script name and an objective.', 'error');
            return;
        }

        console.log(`Requesting script generation for name: '${scriptName}' and objective: '${objective}'`);
        showLoading('Generating script...');

        socket.emit('generate_script', {
            script_name: scriptName,
            objective: objective
        });
    });

    const saveScriptBtn = document.getElementById('save-script-btn');
    saveScriptBtn.style.display = 'none'; // Hide by default

    saveScriptBtn.addEventListener('click', () => {
        const scriptName = scriptNameInput.value.trim();
        const scriptContent = scriptEditor.textContent;

        if (!scriptName || !scriptContent) {
            showNotification('Script name or content is missing.', 'error');
            return;
        }

        socket.emit('save_script', {
            script_name: scriptName,
            script_content: scriptContent
        });
    });

    socket.on('script_saved', (data) => {
        if (data.success) {
            showNotification(`Script '${data.script_name}' saved successfully!`, 'success');
            // Refresh the script list in the Browser view
            socket.emit('request_script_list');
        } else {
            showNotification(`Error saving script: ${data.error}`, 'error');
        }
    });

    socket.on('script_generated', (data) => {
        hideLoading();
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
            saveScriptBtn.style.display = 'block'; // Show the save button

            // Notify the user
            showNotification(`Script '${data.script_name}' generated successfully!`, 'success');

            // Refresh the script list in the Browser view
            socket.emit('request_script_list');

        } else {
            scriptEditor.innerHTML = `<p class="error">Error generating script: ${data.error}</p>`;
            showNotification(`Error generating script: ${data.error}`, 'error');
            saveScriptBtn.style.display = 'none';
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
                // Notify the backend that the user has navigated
                console.log(`[UI] User navigation detected. Notifying backend of new URL: ${newLocation}`);
                socket.emit('user_navigated', { url: newLocation });
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
