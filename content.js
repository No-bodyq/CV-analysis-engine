// content.js — injected into every page
// Listens for a message from popup.js to extract page text

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === "scrapeJobPage") {
    try {
      // Grab all visible text from the page
      const rawText = document.body.innerText;

      // Try to also get the page title for context
      const pageTitle = document.title || "";

      // Limit to 8000 chars to stay within Gemini prompt limits
      const trimmedText = rawText.slice(0, 8000);

      sendResponse({
        success: true,
        text: trimmedText,
        title: pageTitle,
        url: window.location.href
      });
    } catch (err) {
      sendResponse({ success: false, error: err.message });
    }
  }

  // Required for async sendResponse
  return true;
});
