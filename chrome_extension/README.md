# LifeOS Chrome Extension

A Chrome extension that integrates with the LifeOS Assistant backend or works standalone with OpenAI.

## Features

- **Text Selection + Floating Icon**: Select any text on a webpage, click the floating LifeOS icon to chat about it or add it as a task.
- **Side Panel Chat**: Persistent chat interface with streaming AI responses.
- **Task Management**: View and add tasks directly from the side panel.
- **Two Modes**:
  - **With Backend**: Connects to your LifeOS FastAPI backend (requires web app login).
  - **Direct (OpenAI)**: Uses your OpenAI API key directly — no backend required.

## Setup

### 1. Install Dependencies

```bash
cd chrome_extension
npm install
```

### 2. Build the Extension

```bash
npm run build
```

This generates the `dist/` folder with all extension files.

### 3. Load in Chrome

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer mode** (toggle in top-right)
3. Click **Load unpacked** and select the `chrome_extension/dist` folder
4. The LifeOS extension icon should appear in your toolbar

### 4. Configure

1. Click the extension icon in the toolbar to open the settings popup
2. Choose your mode:
   - **With Backend**: Make sure your LifeOS web app is running at `http://localhost:5173` and you are logged in
   - **Direct (OpenAI)**: Enter your OpenAI API key and preferred model (default: `gpt-4o-mini`)

### 5. Use

- Select text on any webpage
- Click the floating **LifeOS icon** that appears
- The side panel opens with the selected text pre-filled
- Chat with AI or click **"Add as Task"** on any message

## Development

```bash
npm run dev      # Start Vite dev mode (limited use for extensions)
npm run build    # Production build
npm run lint     # ESLint
```

## Architecture

| File | Purpose |
|------|---------|
| `background.ts` | Service worker: opens side panel, context menus |
| `content-script.ts` | Detects text selection, injects floating icon |
| `floating-icon/FloatingIcon.ts` | Vanilla Web Component (Shadow DOM) for the floating button |
| `sidepanel/` | React app: chat + tasks |
| `popup/` | React app: settings |
| `lib/api.ts` | Unified API client (backend or OpenAI) |
| `lib/storage.ts` | `chrome.storage.local` wrappers |

## Permissions

- `storage`: Save settings and local history/tasks
- `activeTab`, `scripting`: Inject floating icon, read localStorage from web app
- `sidePanel`: Open Chrome side panel
- Host permissions for `localhost` and `api.openai.com`

## Notes

- The extension reads your JWT token from the LifeOS web app's `localStorage` when in backend mode. Make sure you are logged into the web app first.
- In direct mode, your OpenAI API key is stored in `chrome.storage.local` (encrypted by Chrome's OS-level storage).
- Local history is limited to the last 50 messages to prevent unbounded storage growth.
