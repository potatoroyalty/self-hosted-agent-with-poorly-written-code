document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('theme-toggle');
    const htmlEl = document.documentElement;
    const themeLabel = themeToggle.parentElement.nextElementSibling;

    // Function to set the theme
    function setTheme(theme) {
        htmlEl.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        if (theme === 'dark') {
            themeToggle.checked = true;
            themeLabel.textContent = 'Light Mode';
        } else {
            themeToggle.checked = false;
            themeLabel.textContent = 'Dark Mode';
        }
    }

    // Load the saved theme from localStorage
    const savedTheme = localStorage.getItem('theme') || 'dark'; // Default to dark
    setTheme(savedTheme);

    // Event listener for the theme toggle
    themeToggle.addEventListener('change', () => {
        const newTheme = themeToggle.checked ? 'dark' : 'light';
        setTheme(newTheme);
    });
});
