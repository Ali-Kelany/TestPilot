function elementToHtmlString(element) {
  // Null guard
  if (!element) {
    return 'UNKNOWN ""';
  }
  
  // Escape quotes to prevent malformed output
  const escapeQuotes = (str) => str.replace(/"/g, '\\"');
  
  const tag = element.tagName?.toLowerCase() || 'unknown';
  
  // Map tags to concise role names
  const ROLE_MAP = {
    'a': 'LINK',
    'button': 'BUTTON',
    'input': 'INPUT',
    'select': 'SELECT',
    'textarea': 'TEXTAREA',
    'form': 'FORM',
    'iframe': 'IFRAME',
    'video': 'VIDEO',
    'audio': 'AUDIO'
  };
  
  const role = ROLE_MAP[tag] || element.getAttribute('role')?.toUpperCase() || tag.toUpperCase();
  
  // Extract text content (32 words max)
  let text = '';
  if (tag === 'input' || tag === 'textarea') {
    text = element.getAttribute('placeholder') || element.getAttribute('aria-label') || '';
  } else if (tag === 'select') {
    text = element.getAttribute('aria-label') || '';
  } else {
    text = (element.textContent || '').trim();
  }
  
  // Truncate to 32 words
  const words = text.split(/\s+/).filter(w => w.length > 0);
  if (words.length > 32) {
    text = words.slice(0, 32).join(' ') + '...';
  }
  
  // Build attributes string with only useful attributes
  const usefulAttrs = [];
  
  // Type attribute for inputs
  if (tag === 'input' && element.type) {
    usefulAttrs.push(`type=${element.type}`);
  }
  
  // Value attribute (for inputs with preset values)
  if (tag === 'input' && element.value && element.type !== 'password') {
    usefulAttrs.push(`value="${escapeQuotes(element.value)}"`);
  }
  
  // Placeholder
  const placeholder = element.getAttribute('placeholder');
  if (placeholder) {
    const placeholderWords = placeholder.split(/\s+/).filter(w => w.length > 0);
    const truncatedPlaceholder = placeholderWords.length > 5 
      ? placeholderWords.slice(0, 5).join(' ') + '...'
      : placeholder;
    usefulAttrs.push(`placeholder="${escapeQuotes(truncatedPlaceholder)}"`);
  }
  
  // Href for links
  if (tag === 'a' && element.getAttribute('href')) {
    usefulAttrs.push(`href=${element.getAttribute('href')}`);
  }
  
  // Options for select elements
  if (tag === 'select' && element.options) {
    const options = Array.from(element.options)
      .map(opt => opt.textContent?.trim() || opt.value)
      .filter(Boolean)
      .slice(0, 5); // Show first 5 options max
    
    if (options.length > 0) {
      const optionsText = options.join(',');
      const suffix = element.options.length > 5 ? `,...(${element.options.length - 5} more)` : '';
      usefulAttrs.push(`options=${optionsText}${suffix}`);
    }
  }
  
  // Rows/cols for textarea
  if (tag === 'textarea') {
    if (element.getAttribute('rows')) {
      usefulAttrs.push(`rows=${element.getAttribute('rows')}`);
    }
  }
  
  // Build output string
  const textDisplay = text ? `"${escapeQuotes(text)}"` : '""';
  const attrsDisplay = usefulAttrs.length > 0 ? ' ' + usefulAttrs.join(' ') : '';
  
  return `${role} ${textDisplay}${attrsDisplay}`;
}

window.elementToHtmlString = elementToHtmlString;
