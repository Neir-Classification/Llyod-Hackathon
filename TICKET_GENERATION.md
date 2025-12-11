# Automatic Ticket Generation Feature

## Overview
The system now automatically detects when a user query requires creating a support ticket and generates one in the database with status "open".

## How It Works

### 1. Ticket Detection
When a user sends a query through the `/rag-query` endpoint, the system uses an LLM to analyze whether the query requires ticket creation.

**Queries that CREATE tickets:**
- Filing insurance claims (accidents, damage, loss, injury)
- Requesting policy changes or updates
- Reporting billing issues or payment problems
- Filing formal complaints
- Requesting services (inspections, appraisals, document requests)

**Queries that DON'T create tickets:**
- General information questions
- Coverage or policy detail inquiries
- Clarifications or explanations
- Status checks on existing tickets

### 2. Ticket Categories
- `claim` - Insurance claim filing
- `billing` - Payment or billing issues
- `policy_change` - Policy modification requests
- `complaint` - Formal complaints
- `service_request` - Service or document requests

### 3. Priority Levels
- `low` - Non-urgent requests
- `medium` - Standard priority (default)
- `high` - Important but not immediate
- `urgent` - Time-sensitive issues

## Database Schema
```sql
CREATE TABLE tickets (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    policy_id INTEGER,
    ticket_number VARCHAR(50) UNIQUE,  -- Format: TKT-YYYYMMDD-####
    title VARCHAR(255),
    description TEXT,
    category VARCHAR(50),
    priority VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(20) DEFAULT 'open',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    ...
)
```

## API Response Format
When a ticket is created, the response includes:
```json
{
  "response": "Your AI response text + ticket confirmation message",
  "ticket_created": {
    "ticket_number": "TKT-20251211-1234",
    "title": "Car accident claim filing",
    "category": "claim",
    "priority": "high",
    "status": "open"
  },
  "citations": [...],
  "detected_emotion": "anxious",
  "explainability": {...},
  "safety": {...}
}
```

## User Experience

### For Authenticated Users
1. User asks: "I need to file a claim for my car accident"
2. System detects this is a ticket-worthy request
3. Creates ticket automatically with:
   - Unique ticket number (TKT-YYYYMMDD-####)
   - Category: "claim"
   - Status: "open"
   - Description includes the original query
4. Response includes ticket information
5. User receives confirmation: "✓ I've created ticket TKT-20251211-1234 to handle your claim request. Our team will process this and get back to you soon."

### For Guest Users
- Ticket creation is **disabled** for unauthenticated users
- They receive the standard response without ticket generation
- Encourages users to log in for full service

## Testing

Run the test script:
```bash
python test_ticket_creation.py
```

This will test:
- Ticket creation for claim-related queries
- Ticket creation for policy changes
- Ticket creation for billing issues
- No ticket creation for informational queries

## Admin Dashboard
Administrators can view all tickets through:
- GET `/admin/tickets` - View all tickets in the system
- Tickets show user info, status, priority, and creation date

## Future Enhancements
- Email notifications when tickets are created
- SMS alerts for urgent tickets
- Automatic assignment to available agents
- Ticket status updates via chat
- Ticket history in user profile
