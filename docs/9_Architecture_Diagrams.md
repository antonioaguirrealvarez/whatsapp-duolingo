# 🏗️ Architecture Diagrams

This document contains visual representations of the **WhatsApp-First AI Language Tutor** system architecture, user flows, and data models using Mermaid.js.

## 1. System Context (High-Level)

This diagram shows how the system interacts with external world and services.

```mermaid
graph TD
    User((User))
    WhatsApp[WhatsApp / Twilio]
    System[System Boundary: AI Tutor]
    OpenAI[OpenAI API]
    ElevenLabs[ElevenLabs API]
    Stripe[Stripe API]
    Admin((Admin))

    User <-->|Messages| WhatsApp
    WhatsApp <-->|Webhook/API| System
    System <-->|LLM Calls| OpenAI
    System <-->|TTS/STT| ElevenLabs
    System <-->|Payments| Stripe
    Admin -->|Triggers| System
```

## 2. Container Architecture

This diagram details the internal components of the backend.

```mermaid
graph TB
    subgraph Backend [FastAPI Backend]
        API[API Gateway]
        Orchestrator[Orchestrator Service]
        Router[Intent Router]
        Session[Session Manager]
        
        subgraph Services
            LLM[LLM Gateway]
            Voice[Voice Service]
            Growth[Growth/Analytics]
            Business[Monetization]
        end
        
        subgraph Data_Layer
            UserRepo[User Repo]
            ContentRepo[Content Repo]
        end
    end

    DB[(PostgreSQL)]
    Redis[(Redis Cache)]
    
    WhatsApp -->|Webhook| API
    API -->|Event| Orchestrator
    
    Orchestrator -->|Load Context| Session
    Session <--> Redis
    Session <--> UserRepo
    
    Orchestrator -->|Route| Router
    Router -->|Chat| LLM
    Router -->|Audio| Voice
    
    Orchestrator -->|Check Limits| Business
    
    LLM -->|Get Content| ContentRepo
    ContentRepo <--> DB
    UserRepo <--> DB
```

## 3. Interaction Flow: Basic Chat

The lifecycle of a user message processing.

```mermaid
sequenceDiagram
    participant U as User
    participant WA as WhatsApp/Twilio
    participant API as API Webhook
    participant ORC as Orchestrator
    participant SM as Session Manager
    participant LLM as LLM Gateway
    participant DB as Database

    U->>WA: "Hello"
    WA->>API: POST /webhook
    API->>ORC: handle_event(msg)
    activate ORC
    
    ORC->>SM: load_context(user_id)
    SM->>DB: fetch_user_profile()
    SM->>SM: get_recent_history()
    SM-->>ORC: UserContext
    
    ORC->>LLM: generate_response(context, "Hello")
    activate LLM
    LLM-->>ORC: "Hola! Ready to learn?"
    deactivate LLM
    
    ORC->>SM: save_interaction("Hello", "Hola!")
    ORC->>WA: send_message("Hola! Ready to learn?")
    
    deactivate ORC
    WA->>U: "Hola! Ready to learn?"
```

## 4. Content Generation Pipeline (Async)

How the curriculum is generated in the background.

```mermaid
graph TD
    Start((Start Batch)) --> Pipe[Pipeline Manager]
    Pipe -->|Get Pending Specs| CDB[(Curriculum DB)]
    Pipe -->|Orchestrate| CO[Content Orchestrator]
    
    CO -->|Fetch Schema| Reg[Schema Registry]
    
    CO -->|Generate| Gen[Schema-Aware Generator]
    Gen -->|LLM Call| OpenAI
    OpenAI -->|Raw JSON| Gen
    
    Gen -->|Validate| Val[Content Validator]
    Val -->|Check Schema| Reg
    
    Val --Valid--> Save[Store in DB]
    Val --Invalid--> Retry[Retry Loop]
    
    Save --> MainDB[(Main Database)]
```

## 5. Data Model (ERD)

Key entities in the database.

```mermaid
erDiagram
    USERS ||--o{ USER_PROGRESS : tracks
    USERS {
        uuid id
        string phone_number
        string current_level
        boolean is_premium
        int streak
    }
    
    LESSONS ||--|{ EXERCISES : contains
    LESSONS {
        uuid id
        string topic
        string level
    }
    
    EXERCISES ||--o{ USER_PROGRESS : attempted
    EXERCISES {
        uuid id
        string type
        json content
        string correct_answer
    }
    
    USER_PROGRESS {
        uuid id
        boolean is_correct
        timestamp created_at
    }
    
    CURRICULUM_SPECS ||--|{ EXERCISES : generates
```
