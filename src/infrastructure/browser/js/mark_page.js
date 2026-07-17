(function() {
  'use strict';
  
  // Store references to label elements for cleanup
  let labels = [];
  
  // Configuration
  const CONFIG = {
    minElementArea: 20,
    offScreenThreshold: 500,
    labelZIndex: 2147483647,
  };
  
  // Interactive element selectors
  const INTERACTIVE_SELECTOR = [
    'a', 'button', 'input', 'select', 'textarea',
    '[role="button"]', '[role="link"]', '[role="menuitem"]',
    '[role="tab"]', '[role="checkbox"]', '[role="radio"]',
    '[role="switch"]', '[role="option"]',
    '[onclick]', '[tabindex]:not([tabindex="-1"])',
    'iframe', 'video', 'audio'
  ].join(', ');
  
  const INTERACTIVE_ROLES = new Set([
    'button', 'link', 'menuitem', 'tab', 'checkbox',
    'radio', 'switch', 'option', 'textbox', 'combobox'
  ]);

  /**
   * Remove all marks from the page.
   */
  function unmarkPage() {
    labels.forEach(label => label.remove());
    labels = [];
    document.querySelectorAll('[data-mark]').forEach(el => {
      el.removeAttribute('data-mark');
    });
  }

  /**
   * Check if an element is visible (not hidden by CSS).
   */
  function isVisible(element) {
    const style = getComputedStyle(element);
    return style.display !== 'none' 
      && style.visibility !== 'hidden' 
      && style.opacity !== '0';
  }

  /**
   * Check if element appears interactive (clickable).
   */
  function isInteractive(element) {
    // Has click handler
    if (element.onclick) return true;
    
    // Has pointer cursor
    if (getComputedStyle(element).cursor === 'pointer') return true;
    
    // Has interactive ARIA role
    const role = element.getAttribute('role');
    if (role && INTERACTIVE_ROLES.has(role)) return true;
    
    return false;
  }

  /**
   * Extract accessibility state from an element.
   */
  function getElementState(element) {
    const state = {};
    
    // Disabled state
    if (element.disabled || element.getAttribute('aria-disabled') === 'true') {
      state.disabled = true;
    }
    
    // Readonly state
    if (element.readOnly || element.hasAttribute('readonly')) {
      state.readonly = true;
    }
    
    // Checked state (checkboxes, radios)
    if (element.type === 'checkbox' || element.type === 'radio') {
      state.checked = element.checked;
    } else if (element.getAttribute('aria-checked') !== null) {
      state.checked = element.getAttribute('aria-checked') === 'true';
    }
    
    // Expanded state (dropdowns, accordions)
    if (element.getAttribute('aria-expanded') !== null) {
      state.expanded = element.getAttribute('aria-expanded') === 'true';
    }
    
    return state;
  }

  /**
   * Get a description for the element from various attributes.
   */
  function getDescription(element) {
    return element.getAttribute('placeholder')
      || element.getAttribute('aria-label')
      || element.getAttribute('title')
      || element.querySelector('img')?.getAttribute('alt')
      || (element.tagName === 'IMG' ? element.getAttribute('alt') : null)
      || '';
  }

  /**
   * Calculate visible bounding box for an element.
   */
  function getVisibleRect(element, viewport) {
    const rects = element.getClientRects();
    if (rects.length === 0) return null;
    
    // Use the first rect that's actually visible
    for (const rect of rects) {
      // Check if element is at center point
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;
      const elAtCenter = document.elementFromPoint(centerX, centerY);
      
      if (elAtCenter === element || element.contains(elAtCenter)) {
        return {
          left: Math.max(0, rect.left),
          top: Math.max(0, rect.top),
          right: Math.min(viewport.width, rect.right),
          bottom: Math.min(viewport.height, rect.bottom),
          width: Math.min(viewport.width, rect.right) - Math.max(0, rect.left),
          height: Math.min(viewport.height, rect.bottom) - Math.max(0, rect.top),
        };
      }
    }
    
    return null;
  }

  /**
   * Check if element is off-screen or nearby.
   */
  function checkOffScreen(rect, viewport) {
    const threshold = CONFIG.offScreenThreshold;
    
    // Completely off-screen (not even nearby)
    if (rect.bottom < -threshold || rect.top > viewport.height + threshold ||
        rect.right < -threshold || rect.left > viewport.width + threshold) {
      return { isOffScreen: true, isNearby: false };
    }
    
    // Off-screen but nearby (within threshold)
    const isOffScreen = rect.bottom < 0 || rect.top > viewport.height ||
                        rect.right < 0 || rect.left > viewport.width;
    
    return { isOffScreen, isNearby: true };
  }

  /**
   * Generate a random color for element highlighting.
   */
  function randomColor() {
    const hue = Math.floor(Math.random() * 360);
    return `hsl(${hue}, 70%, 50%)`;
  }

  /**
   * Create a visual label overlay for a marked element.
   */
  function createLabel(index, rect, color) {
    const container = document.createElement('div');
    container.style.cssText = `
      position: fixed;
      left: ${rect.left}px;
      top: ${rect.top}px;
      width: ${rect.width}px;
      height: ${rect.height}px;
      outline: 2px dashed ${color};
      pointer-events: none;
      box-sizing: border-box;
      z-index: ${CONFIG.labelZIndex};
    `;
    
    const label = document.createElement('span');
    label.textContent = index;
    label.style.cssText = `
      position: absolute;
      top: -20px;
      left: 0;
      background: ${color};
      color: white;
      padding: 2px 6px;
      font-size: 12px;
      font-weight: bold;
      border-radius: 3px;
      font-family: monospace;
    `;
    
    container.appendChild(label);
    return container;
  }

  /**
   * Main function: mark all interactive elements on the page.
   * Returns an array of mark data for the agent.
   */
  function markPage() {
    unmarkPage();
    
    const viewport = {
      width: window.innerWidth,
      height: window.innerHeight,
    };
    
    // Find all potentially interactive elements
    const candidates = new Set(document.querySelectorAll(INTERACTIVE_SELECTOR));
    
    // Also find elements with interactive behavior
    const walker = document.createTreeWalker(
      document.body,
      NodeFilter.SHOW_ELEMENT,
      { acceptNode: (node) => {
        if (candidates.has(node)) return NodeFilter.FILTER_SKIP;
        return isInteractive(node) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_SKIP;
      }}
    );
    
    let node;
    while ((node = walker.nextNode())) {
      candidates.add(node);
    }
    
    // Process candidates and collect valid elements
    const elements = [];
    
    for (const element of candidates) {
      if (!isVisible(element)) continue;
      
      const rect = getVisibleRect(element, viewport);
      if (!rect || rect.width * rect.height < CONFIG.minElementArea) continue;
      
      const { isOffScreen, isNearby } = checkOffScreen(rect, viewport);
      if (!isNearby) continue;
      
      elements.push({
        element,
        rect,
        isOffScreen,
        role: element.getAttribute('role') || element.tagName.toLowerCase(),
        state: getElementState(element),
        description: getDescription(element),
      });
    }
    
    // Filter out parent elements that fully contain children
    // (prefer the more specific child elements)
    const filtered = elements.filter((item, _, arr) => {
      const hasInteractiveChild = arr.some(other => 
        other !== item && 
        item.element.contains(other.element) &&
        item.element !== other.element
      );
      
      // Keep if no interactive children, or if it has its own click handler
      return !hasInteractiveChild || item.element.onclick;
    });
    
    // Create marks for visible elements
    const marks = [];
    let index = 0;
    
    for (const item of filtered) {
      if (item.isOffScreen) continue;
      
      const color = randomColor();
      const label = createLabel(index, item.rect, color);
      document.body.appendChild(label);
      labels.push(label);
      
      item.element.setAttribute('data-mark', String(index));
      
      marks.push({
        mark: String(index),
        element: window.elementToHtmlString(item.element),
        role: item.role,
        state: item.state,
        description: item.description,
        isOffScreen: item.isOffScreen,
      });
      
      index++;
    }
    
    return marks;
  }

  // Expose functions globally
  window.markPage = markPage;
  window.unmarkPage = unmarkPage;
})();