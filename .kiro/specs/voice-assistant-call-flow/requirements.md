# Requirements Document

## Introduction

This document specifies the requirements for a comprehensive voice assistant call flow system that integrates with FreeSWITCH telephony infrastructure. The system processes Russian language voice commands through a microservices architecture with ASR, NLU, Dialog, and TTS services, providing real-time voice interaction capabilities for task management and notifications.

## Glossary

- **Gateway_Service**: Entry point service handling FreeSWITCH integration and session management
- **ASR_Service**: Automatic Speech Recognition service for converting audio to text
- **NLU_Service**: Natural Language Understanding service for intent extraction
- **Dialog_Service**: Conversation management service with state tracking
- **TTS_Service**: Text-to-Speech service for Russian speech synthesis
- **Session**: A call session representing one complete voice interaction
- **Audio_Chunk**: 200ms segments of audio data from RTP stream
- **Intent**: Classified user intention with confidence score
- **Partial_Result**: Intermediate ASR transcription during streaming
- **Final_Result**: Complete ASR transcription for a speech segment
- **Storage_Proxy**: Service managing PostgreSQL persistence operations
- **Notification_Worker**: Async service handling Telegram notifications via RabbitMQ

## Requirements

### Requirement 1: Call Session Management

**User Story:** As a user, I want to initiate voice calls that are properly managed throughout the interaction, so that I can have consistent voice assistant sessions.

#### Acceptance Criteria

1. WHEN a SIP call is received by FreeSWITCH, THE Gateway_Service SHALL create a new Session with unique identifier
2. WHEN a Session is created, THE Gateway_Service SHALL play a Russian greeting message to establish communication
3. WHEN a call ends or times out, THE Gateway_Service SHALL properly terminate the Session and clean up resources
4. WHILE a Session is active, THE Gateway_Service SHALL maintain session state and routing information
5. IF a Session encounters an error, THEN THE Gateway_Service SHALL log the error and gracefully terminate the session

### Requirement 2: Real-time Audio Processing

**User Story:** As a user, I want my voice to be processed in real-time during calls, so that I can have natural conversations with the voice assistant.

#### Acceptance Criteria

1. WHEN RTP audio is received, THE Gateway_Service SHALL split it into 200ms Audio_Chunks
2. WHEN an Audio_Chunk is ready, THE Gateway_Service SHALL stream it to ASR_Service via gRPC bidirectional streaming
3. WHILE audio is streaming, THE ASR_Service SHALL generate Partial_Results for immediate feedback
4. WHEN speech segment ends, THE ASR_Service SHALL produce a Final_Result with complete transcription
5. THE Gateway_Service SHALL maintain audio streaming with latency under 300ms for real-time interaction

### Requirement 3: Speech Recognition Processing

**User Story:** As a user, I want my Russian speech to be accurately recognized, so that the voice assistant can understand my commands.

#### Acceptance Criteria

1. WHEN an Audio_Chunk is received, THE ASR_Service SHALL process it using the configured ASR engine (Vosk or Whisper.cpp)
2. WHILE processing audio streams, THE ASR_Service SHALL generate Partial_Results for ongoing speech
3. WHEN a speech segment is complete, THE ASR_Service SHALL produce a Final_Result with confidence score
4. THE ASR_Service SHALL optimize processing for Russian language phonemes and vocabulary
5. IF audio quality is insufficient, THEN THE ASR_Service SHALL return low confidence scores to trigger error recovery

### Requirement 4: Intent Classification and Understanding

**User Story:** As a user, I want the system to understand the meaning of my voice commands, so that it can perform the correct actions.

#### Acceptance Criteria

1. WHEN a Final_Result is received from ASR, THE NLU_Service SHALL extract Intent with confidence score
2. THE NLU_Service SHALL classify intents for shopping list management, reminders, and general queries
3. WHEN Intent confidence is above 0.7, THE NLU_Service SHALL proceed with intent processing
4. WHEN Intent confidence is below 0.7, THE NLU_Service SHALL mark the result for error recovery
5. THE NLU_Service SHALL extract entities (items, dates, quantities) from the transcribed text

### Requirement 5: Dialog Management and State Tracking

**User Story:** As a user, I want to have coherent conversations with the voice assistant that remember context, so that I can complete complex tasks across multiple exchanges.

#### Acceptance Criteria

1. WHEN an Intent is received, THE Dialog_Service SHALL determine the appropriate response based on current conversation state
2. WHILE managing conversations, THE Dialog_Service SHALL maintain context across multiple user turns
3. WHEN a task requires confirmation, THE Dialog_Service SHALL prompt the user and wait for response
4. THE Dialog_Service SHALL handle multi-turn conversations for complex shopping list operations
5. IF an error occurs during dialog processing, THEN THE Dialog_Service SHALL provide appropriate error recovery prompts

### Requirement 6: Speech Synthesis and Response

**User Story:** As a user, I want to receive clear Russian speech responses from the voice assistant, so that I can understand the system's feedback and confirmations.

#### Acceptance Criteria

1. WHEN a response text is generated, THE TTS_Service SHALL synthesize it into Russian speech using Silero TTS
2. THE TTS_Service SHALL generate audio with natural Russian pronunciation and intonation
3. WHEN TTS audio is ready, THE Gateway_Service SHALL stream it back to FreeSWITCH for playback
4. THE TTS_Service SHALL optimize synthesis speed to maintain conversation flow
5. THE TTS_Service SHALL handle special characters and numbers appropriately in Russian context

### Requirement 7: Data Persistence and Storage

**User Story:** As a user, I want my shopping lists and reminders to be saved persistently, so that I can access them later and receive notifications.

#### Acceptance Criteria

1. WHEN shopping list items are added or modified, THE Storage_Proxy SHALL persist changes to PostgreSQL database
2. WHEN reminders are created, THE Storage_Proxy SHALL store them with associated timestamps and user information
3. THE Storage_Proxy SHALL maintain data integrity during concurrent access from multiple services
4. THE Storage_Proxy SHALL provide transactional operations for complex data modifications
5. WHEN data queries are made, THE Storage_Proxy SHALL return current state with appropriate error handling

### Requirement 8: Asynchronous Notification System

**User Story:** As a user, I want to receive Telegram notifications about my shopping list updates, so that I can stay informed about changes made through voice commands.

#### Acceptance Criteria

1. WHEN shopping list changes occur, THE Dialog_Service SHALL publish notification events to RabbitMQ
2. WHEN notification events are received, THE Notification_Worker SHALL process them asynchronously
3. THE Notification_Worker SHALL send formatted Telegram messages with shopping list updates
4. THE Notification_Worker SHALL handle Telegram API failures gracefully with retry logic
5. THE Notification_Worker SHALL maintain notification delivery status for monitoring

### Requirement 9: Error Recovery and Robustness

**User Story:** As a user, I want the system to handle errors gracefully and help me when speech recognition fails, so that I can still accomplish my tasks.

#### Acceptance Criteria

1. WHEN ASR confidence is low, THE Dialog_Service SHALL prompt the user to repeat their request
2. WHEN NLU fails to extract intent, THE Dialog_Service SHALL ask clarifying questions
3. WHEN service communication fails, THE Gateway_Service SHALL provide appropriate error messages
4. THE Gateway_Service SHALL implement timeout handling for unresponsive downstream services
5. WHEN critical errors occur, THE Gateway_Service SHALL log detailed error information for debugging

### Requirement 10: Service Communication and Integration

**User Story:** As a system administrator, I want services to communicate reliably through well-defined interfaces, so that the system operates cohesively and can be monitored effectively.

#### Acceptance Criteria

1. THE Gateway_Service SHALL communicate with downstream services using gRPC with Protocol Buffers
2. WHEN services start up, THEY SHALL register with the service discovery mechanism
3. THE Gateway_Service SHALL implement health checks for all downstream services
4. WHEN service calls fail, THE Gateway_Service SHALL implement circuit breaker patterns for resilience
5. THE Gateway_Service SHALL log service communication metrics for monitoring and analytics

### Requirement 11: Performance and Scalability

**User Story:** As a system administrator, I want the system to handle multiple concurrent calls efficiently, so that users experience consistent performance.

#### Acceptance Criteria

1. THE Gateway_Service SHALL handle multiple concurrent Sessions without performance degradation
2. WHEN processing audio streams, THE ASR_Service SHALL maintain processing latency under 200ms per chunk
3. THE Dialog_Service SHALL respond to intent processing requests within 100ms
4. THE TTS_Service SHALL generate speech synthesis within 500ms for typical responses
5. THE Storage_Proxy SHALL handle database operations with connection pooling for optimal performance

### Requirement 12: Russian Language Optimization

**User Story:** As a Russian-speaking user, I want the voice assistant to understand and respond in natural Russian, so that I can interact comfortably in my native language.

#### Acceptance Criteria

1. THE ASR_Service SHALL use Russian language models optimized for telephony audio quality
2. THE NLU_Service SHALL recognize Russian intent patterns and entity extraction
3. THE TTS_Service SHALL generate natural Russian speech with appropriate stress and intonation
4. THE Dialog_Service SHALL provide responses in grammatically correct Russian
5. THE Dialog_Service SHALL handle Russian-specific linguistic patterns like case declensions in entity recognition