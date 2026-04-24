# Data Model: LifeOS Assistant

## Entities

### User
Represents the authorized account.
- `id`: UUID (Primary Key)
- `email`: String (Unique, e.g., `vinhho2508@gmail.com`)
- `created_at`: Timestamp

### Task
Represents an item on the board and for reminders.
- `id`: UUID (Primary Key)
- `user_id`: UUID (Foreign Key -> User)
- `title`: String
- `description`: Text (Optional)
- `status`: Enum (`TODO`, `IN_PROGRESS`, `DONE`)
- `due_date`: Timestamp (Optional)
- `reminder_sent`: Boolean (Default: False)
- `created_at`: Timestamp

### Document
A source file uploaded for RAG.
- `id`: UUID (Primary Key)
- `user_id`: UUID (Foreign Key -> User)
- `filename`: String
- `status`: Enum (`UPLOADED`, `DIGESTING`, `READY`, `ERROR`)
- `created_at`: Timestamp

### DocumentChunk
Vectorized chunks of a document for retrieval.
- `id`: UUID (Primary Key)
- `document_id`: UUID (Foreign Key -> Document)
- `content`: Text
- `embedding`: Vector(1536) (pgvector, assumes OpenAI embeddings or similar)

### Message
Chat history records.
- `id`: UUID (Primary Key)
- `user_id`: UUID (Foreign Key -> User)
- `sender`: Enum (`USER`, `ASSISTANT`)
- `platform`: Enum (`WEB`, `SLACK`)
- `text`: Text
- `timestamp`: Timestamp

## Relationships
- A User has many Tasks, Documents, and Messages.
- A Document has many DocumentChunks.
- A Task is associated with one User.
