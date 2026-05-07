// background.js — service worker (minimal, popup handles most logic)
chrome.runtime.onInstalled.addListener(() => {
  console.log("CV Engine Job Scraper installed.");
});
