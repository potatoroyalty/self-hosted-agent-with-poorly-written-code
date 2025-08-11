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

    const startBtn = document.getElementById('start-btn');
    startBtn.addEventListener('click', () => {
        const objective = document.getElementById('instruction-input').value;
        if (objective) {
            console.log('Start button clicked with objective:', objective);
            socket.emit('start_agent', { objective: objective });
        } else {
            alert("Please enter an objective in the generator view.");
        }
    });

    const views = document.querySelectorAll('.view');
    const navLinks = document.querySelectorAll('.nav-link');

    const browserLink = document.getElementById('view-browser-link');
    const generatorLink = document.getElementById('view-generator-link');

    const browserView = document.getElementById('browser-view');
    const generatorView = document.getElementById('generator-view');

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

    // Set the initial view
    switchView(browserView, browserLink);
});
