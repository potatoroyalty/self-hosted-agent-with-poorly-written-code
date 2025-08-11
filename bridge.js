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

    const socket = io('/bridge'); // Use a dedicated namespace for the bridge
    let isRecording = false;

    socket.on('connect', () => {
        console.log("Bridge connected to backend via Socket.IO.");
    });

    // Listen for control messages from the backend
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

    socket.on('connect_error', (error) => {
        console.error("Bridge connection error:", error);
    });

    function getSelector(element) {
        if (!element || !element.tagName) return '';
        if (element.id) {
            // If the ID is unique, just use that.
            try {
                if (document.querySelectorAll(`#${CSS.escape(element.id)}`).length === 1) {
                    return `#${CSS.escape(element.id)}`;
                }
            } catch (e) {
                // Handle invalid IDs
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
                // Handle complex selectors that might fail during construction
                path = 'body';
                break;
            }

            element = element.parentElement;
        }
        return path;
    }

    function recordEvent(event) {
        // We only care about user-initiated events and if recording is active.
        if (!event.isTrusted || !isRecording) {
            return;
        }

        const selector = getSelector(event.target);
        const eventDetails = {
            type: event.type,
            selector: selector,
            value: event.target.value,
            inputValue: event.type === 'input' ? event.target.value : undefined,
            tagName: event.target.tagName.toLowerCase(),
            timestamp: Date.now()
        };

        // The socket connection check is still a good idea.
        if (socket.connected) {
            socket.emit('record_action', eventDetails);
        }
    }

    // Use capture phase to catch events early.
    document.addEventListener('click', recordEvent, { capture: true });
    document.addEventListener('input', recordEvent, { capture: true });

})();
