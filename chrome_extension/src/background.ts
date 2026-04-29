import type { SelectedTextInfo } from '@/types'

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === 'OPEN_SIDE_PANEL') {
    if (sender.tab?.windowId) {
      chrome.sidePanel.open({ windowId: sender.tab.windowId })
    }
    sendResponse({ success: true })
  }
  return false
})

// Context menus as fallback
chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'lifeos-chat',
    title: 'Chat about this',
    contexts: ['selection'],
  })
  chrome.contextMenus.create({
    id: 'lifeos-task',
    title: 'Add as Task',
    contexts: ['selection'],
  })
})

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (!tab?.windowId) return
  const text = info.selectionText || ''
  if (info.menuItemId === 'lifeos-chat' || info.menuItemId === 'lifeos-task') {
    const selected: SelectedTextInfo = {
      text,
      url: info.pageUrl || '',
      title: tab.title || '',
    }
    chrome.storage.local.set({
      lifeos_selected: selected,
      lifeos_context_action: info.menuItemId === 'lifeos-task' ? 'task' : 'chat',
    })
    chrome.sidePanel.open({ windowId: tab.windowId })
  }
})
