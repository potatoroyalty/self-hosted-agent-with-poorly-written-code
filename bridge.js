(function() {
    // Don't run if the bridge is already injected
    if (window.myBrowserBridge) {
        return;
    }
    // Check if socket.io client is loaded. If not, this script can't run.
    if (typeof io === 'undefined') {
        console.error("Socket.IO client not loaded. Bridge cannot connect.");
        return;
    }
    window.myBrowserBridge = true;

    console.log("Bridge script injected and running.");

    const socket = io('/bridge');
    let isRecording = false;

    // --- Utility Functions ---

    function getSelector(element) {
        if (!element || !element.tagName) return '';
        if (element.id) {
            try {
                if (document.querySelectorAll(`#${CSS.escape(element.id)}`).length === 1) {
                    return `#${CSS.escape(element.id)}`;
                }
            } catch (e) {
                return 'body';
            }
        }

        let path = '';
        while (element && element.parentElement) {
            let selector = element.tagName.toLowerCase();
            const siblings = Array.from(element.parentElement.children);
            const sameTagSiblings = siblings.filter(e => e.tagName === element.tagName);

            if (sameTagSiblings.length > 1) {
                const index = sameTagSiblings.indexOf(element);
                selector += `:nth-of-type(${index + 1})`;
            }

            path = selector + (path ? ' > ' + path : '');

            try {
                if (document.querySelectorAll(path).length === 1) {
                    break;
                }
            } catch (e) {
                path = 'body';
                break;
            }

            element = element.parentElement;
        }
        return path;
    }

    // --- Event Recording ---

    function recordEvent(event) {
        if (!event.isTrusted || !isRecording) {
            return;
        }

        const selector = getSelector(event.target);
        const eventDetails = {
            type: event.type,
            selector: selector,
            value: event.target.value,
            inputValue: event.type === 'input' ? event.target.value : undefined,
            key: event.type === 'keydown' ? event.key : undefined,
            tagName: event.target.tagName.toLowerCase(),
            timestamp: Date.now()
        };

        if (socket.connected) {
            socket.emit('record_action', eventDetails);
        }
    }

    // --- Agent Command Execution ---

    socket.on('goto', (data) => {
        try {
            console.log(`[Bridge] Navigating to: ${data.url}`);
            window.location.href = data.url;
            // The 'load' event on the iframe in renderer.js will handle reinjection.
            // No explicit success message needed as the page will reload.
        } catch (error) {
            console.error('[Bridge] Goto failed:', error);
            socket.emit('action_response', { success: false, error: error.message, action: 'goto' });
        }
    });

    socket.on('click', (data) => {
        try {
            console.log(`[Bridge] Clicking element with label: ${data.label}`);
            const element = window.labeledElements[data.label];
            if (!element) {
                throw new Error(`Element with label ${data.label} not found.`);
            }
            element.click();
            socket.emit('action_response', { success: true, action: 'click' });
        } catch (error) {
            console.error('[Bridge] Click failed:', error);
            socket.emit('action_response', { success: false, error: error.message, action: 'click' });
        }
    });

    socket.on('type', (data) => {
        try {
            console.log(`[Bridge] Typing in element with label: ${data.label}`);
            const element = window.labeledElements[data.label];
            if (!element) {
                throw new Error(`Element with label ${data.label} not found.`);
            }
            element.value = data.text;
            // Dispatch input event to ensure frameworks like React update their state
            element.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
            element.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
            socket.emit('action_response', { success: true, action: 'type' });
        } catch (error) {
            console.error('[Bridge] Type failed:', error);
            socket.emit('action_response', { success: false, error: error.message, action: 'type' });
        }
    });

    socket.on('select', (data) => {
        try {
            console.log(`[Bridge] Selecting in element with label: ${data.label}`);
            const element = window.labeledElements[data.label];
            if (!element) {
                throw new Error(`Element with label ${data.label} not found.`);
            }
            element.value = data.value;
            // Dispatch change event to ensure frameworks like React update their state
            element.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
            socket.emit('action_response', { success: true, action: 'select' });
        } catch (error) {
            console.error('[Bridge] Select failed:', error);
            socket.emit('action_response', { success: false, error: error.message, action: 'select' });
        }
    });

    socket.on('scroll', (data) => {
        try {
            console.log(`[Bridge] Scrolling: ${data.direction}`);
            const scrollAmount = data.direction === 'down' ? window.innerHeight : -window.innerHeight;
            window.scrollBy(0, scrollAmount);
            socket.emit('action_response', { success: true, action: 'scroll' });
        } catch (error) {
            console.error('[Bridge] Scroll failed:', error);
            socket.emit('action_response', { success: false, error: error.message, action: 'scroll' });
        }
    });

    socket.on('get_observation', async () => {
        console.log('[Bridge] Received get_observation request.');
        try {
            // Reset labeled elements
            window.labeledElements = {};

            // 1. Get interactive elements
            const interactiveElements = Array.from(document.querySelectorAll(
                "a, button, input, textarea, select, [role='button'], [role='link'], " +
                "[role='tab'], [role='checkbox'], [role='menuitem'], [role='option'], [role='switch']"
            ));

            const elementsData = interactiveElements
                .map((el, index) => {
                    const rect = el.getBoundingClientRect();
                    // Filter out invisible or zero-size elements
                    if (rect.width > 0 && rect.height > 0 && rect.top >= 0 && rect.left >= 0 && rect.bottom <= window.innerHeight && rect.right <= window.innerWidth) {
                        const label = index + 1;
                        window.labeledElements[label] = el; // Store element with its label
                        return {
                            label: label,
                            selector: getSelector(el),
                            box: { x: rect.x, y: rect.y, width: rect.width, height: rect.height },
                            tag: el.tagName.toLowerCase(),
                            aria_label: el.getAttribute('aria-label'),
                            name: el.name,
                            text: el.innerText,
                            value: el.value,
                            href: el.href, // Will be undefined for non-links, which is fine
                        };
                    }
                    return null;
                })
                .filter(Boolean); // Filter out nulls

            // 2. Take screenshot with html2canvas
            const canvas = await html2canvas(document.body, {
                useCORS: true,
                allowTaint: true,
                logging: false,
                scrollX: -window.scrollX,
                scrollY: -window.scrollY,
                windowWidth: document.documentElement.offsetWidth,
                windowHeight: document.documentElement.offsetHeight
            });
            const screenshot = canvas.toDataURL('image/png').split(',')[1];

            // 3. Send data back
            console.log(`[Bridge] Sending observation data to backend (${elementsData.length} elements found).`);
            socket.emit('observation_response', {
                success: true,
                screenshot: screenshot,
                elements: elementsData
            });

        } catch (error) {
            console.error('[Bridge] Get observation failed:', error);
            socket.emit('observation_response', { success: false, error: error.message });
        }
    });

    // --- Lifecycle and Recording Setup ---

    let bridgeSettings = {}; // To store settings from the backend

    socket.on('update_bridge_settings', (settings) => {
        console.log('[Bridge] Received settings update:', settings);
        bridgeSettings = settings;
        // NOTE: Actually implementing these settings on the fly is complex.
        // For example, disabling images or JS would likely require a page reload
        // with new browser context settings, which is not handled here.
        // This handler currently just proves the connection is made.
    });

    socket.on('connect', () => {
        console.log("Bridge connected to backend via Socket.IO.");
    });

    socket.on('start_recording_bridge', () => {
        console.log('[Bridge] Recording enabled.');
        isRecording = true;
    });

    socket.on('stop_recording_bridge', () => {
        console.log('[Bridge] Recording disabled.');
        isRecording = false;
    });

    socket.on('disconnect', () => {
        console.log("Bridge disconnected from backend.");
    });

    document.addEventListener('click', recordEvent, { capture: true });
    document.addEventListener('input', recordEvent, { capture: true });
    document.addEventListener('change', recordEvent, { capture: true });
    document.addEventListener('submit', recordEvent, { capture: true });
    document.addEventListener('keydown', recordEvent, { capture: true });
    document.addEventListener('scroll', recordEvent, { capture: true });

})();
