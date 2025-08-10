/**
 * Richer Input via Deterministic Pre-Processing
 *
 * This script simplifies and enriches the DOM for more reliable AI processing.
 * It performs three main tasks:
 * 1.  HTML Metadata Injection: Labels elements with essential properties like tag, role, and clickability.
 * 2.  Semantic Region Tagging: Identifies and tags primary regions (header, footer, main content).
 * 3.  Visual Simplification (Reader Mode): Removes ads, pop-ups, and complex styling to focus on content.
 *
 * The final output is a single JSON object that can be passed to the AI model.
 */

/**
 * Injects metadata into each element, providing a structured view of the DOM.
 * @returns {Array<Object>} An array of objects, each representing a labeled element.
 */
function labelElementsWithMetadata() {
    const elements = document.querySelectorAll('*');
    const labeledElements = [];

    elements.forEach((element, index) => {
        // Ignore script and style tags as they don't contain renderable content
        if (element.tagName.toLowerCase() === 'script' || element.tagName.toLowerCase() === 'style') {
            return;
        }

        const role = element.getAttribute('role') || 'unknown';
        // A more reliable way to determine clickability is to check the computed cursor style.
        const isClickable = window.getComputedStyle(element).cursor === 'pointer' || (element instanceof HTMLElement && element.tabIndex !== -1);
        const text = element.innerText ? element.innerText.trim().substring(0, 200) : '';

        labeledElements.push({
            index: index + 1,
            text: text,
            tag: element.tagName.toLowerCase(),
            role: role,
            clickable: isClickable,
        });
    });

    return labeledElements;
}

/**
 * Identifies and returns the primary semantic regions of the page.
 * @returns {Object} An object containing references to the main page regions.
 */
function tagSemanticRegions() {
    const regions = {};

    // More robust selectors for common semantic regions, including ARIA roles
    const selectors = {
        header: 'header, [role="banner"]',
        footer: 'footer, [role="contentinfo"]',
        main: 'main, [role="main"]',
        navigation: 'nav, [role="navigation"]',
        sidebar: 'aside, [role="complementary"]'
    };

    for (const regionName in selectors) {
        regions[regionName] = document.querySelector(selectors[regionName]);
    }

    return regions;
}

/**
 * Simplifies the page by removing non-essential elements and styles.
 * This function should be called before other processing to ensure a clean slate.
 * @param {Object} regions - The regions object from tagSemanticRegions.
 */
function simplifyPage(regions) {
    // Selectors for ads, pop-ups, and other clutter
    const clutterSelectors = [
        '.ad', '.ads', '[data-ad]', '[id*="ad"]',
        '.popup', '[data-popup]', '[aria-modal="true"]',
        '.sidebar', '[data-sidebar]', '[class*="sidebar"]',
        'iframe[src*="ads"]', 'iframe[src*="googleads"]'
    ];

    // Remove clutter
    clutterSelectors.forEach(selector =>
        document.querySelectorAll(selector).forEach(el => el.remove())
    );

    // Remove navigation elements if they are not inside the main content area
    if (regions.navigation && regions.mainContent && !regions.mainContent.contains(regions.navigation)) {
        regions.navigation.remove();
    }

    // Apply a simple, clean "reader mode" style
    document.body.style.fontFamily = 'Arial, sans-serif';
    document.body.style.fontSize = '16px';
    document.body.style.backgroundColor = '#ffffff';
    document.body.style.margin = '0';
    document.body.style.padding = '20px';
}

/**
 * Main function to prepare the page for AI processing.
 * It orchestrates the simplification, tagging, and labeling process.
 * @returns {Promise<Object>} A promise that resolves to the full page description object.
 */
async function preparePageForAI() {
    const regions = tagSemanticRegions();
    simplifyPage(regions);
    const finalRegions = tagSemanticRegions(); // Re-tag after simplification
    const labeledElements = labelElementsWithMetadata();

    const serializableRegions = {};
    for (const key in finalRegions) {
        serializableRegions[key] = !!finalRegions[key];
    }

    return {
        regions: serializableRegions,
        labeledElements: labeledElements,
    };
}

// The script returns the result of the main function call.
// When executed via Playwright's page.evaluate(), this will be the resolved value.
preparePageForAI();