# API Contracts: LifeOS Assistant

## Authentication

### POST `/auth/login`
- **Request**: `{ "token": "google_oauth_token" }`
- **Response**: `{ "access_token": "jwt", "token_type": "bearer" }`
- **Rules**: Must verify JWT from Google and check email == `vinhho2508@gmail.com`.

## Tasks

### GET `/tasks`
- **Response**: `[ { "id": "...", "title": "...", "status": "TODO", "due_date": "..." } ]`

### POST `/tasks`
- **Request**: `{ "title": "...", "description": "...", "status": "TODO", "due_date": "..." }`
- **Response**: Created task object.

### PUT `/tasks/{id}`
- **Request**: `{ "title": "...", "status": "WORKING", "due_date": "..." }`
- **Response**: Updated task object.

### DELETE `/tasks/{id}`
- **Response**: `204 No Content`

## Chat

### POST `/chat`
- **Request**: `{ "message": "...", "platform": "WEB" }`
- **Response**: `{ "reply": "...", "metadata": { "extracted_task": "...", "reminder_set": true } }`

### GET `/chat/history`
- **Response**: `[ { "sender": "USER", "text": "...", "timestamp": "..." } ]`

## Documents (RAG)

### POST `/documents/upload`
- **Request**: `Multipart form data (file)`
- **Response**: `{ "document_id": "...", "status": "UPLOADED" }`

### POST `/documents/digest`
- **Request**: `{ "text": "...", "title": "..." }`
- **Response**: `{ "document_id": "...", "status": "DIGESTING" }`

## Slack Integration

### POST `/slack/events`
- **Description**: Standard Slack Events API endpoint.
- **Handling**: Validates slack signature and routes to internal `/chat` logic.
