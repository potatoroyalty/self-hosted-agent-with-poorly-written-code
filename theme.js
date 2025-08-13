document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('theme-toggle');
    const htmlEl = document.documentElement;
    const themeLabel = document.getElementById('theme-label'); // Use the new ID

    // Function to set the theme
    function setTheme(theme) {
        htmlEl.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);

        // Check if themeToggle and themeLabel exist before using them
        if (themeToggle) {
            themeToggle.checked = (theme === 'dark');
        }
        if (themeLabel) {
            themeLabel.textContent = (theme === 'dark') ? 'Light Mode' : 'Dark Mode';
        }
    }

    // Load the saved theme from localStorage
    const savedTheme = localStorage.getItem('theme') || 'dark'; // Default to dark
    setTheme(savedTheme);

    // Event listener for the theme toggle
    if (themeToggle) {
        themeToggle.addEventListener('change', () => {
            const newTheme = themeToggle.checked ? 'dark' : 'light';
            setTheme(newTheme);
        });
    }
});
