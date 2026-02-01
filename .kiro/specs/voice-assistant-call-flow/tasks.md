# Implementation Plan: Voice Assistant Call Flow System

## Overview

This implementation plan converts the voice assistant call flow design into discrete coding tasks for a microservices architecture. The plan follows an incremental approach, building core infrastructure first, then implementing individual services, and finally integrating them into a complete call flow system. Each task builds on previous work and includes property-based testing to ensure correctness.

## Tasks

- [x] 1. Set up project structure and voice_assistant components
  - Create directory structure following DDD principles
  - Implement voice_assistant domain entities (CallSession, AudioChunk, Intent, etc.)
  - Set up Protocol Buffer definitions for gRPC communication
  - Configure dependency injection container with rodi
  - Set up pytest and Hypothesis for property-based testing
  - _Requirements: 10.1, 10.2_

- [x] 2. Implement core Gateway Service infrastructure
  - [x] 2.1 Create Gateway Service FastAPI application with session management
    - Implement CallSession entity with UUID generation and state tracking
    - Create session storage using Redis for distributed state
    - Implement session lifecycle management (create, update, cleanup)
    - _Requirements: 1.1, 1.3, 1.4_

  - [ ]* 2.2 Write property test for session lifecycle management
    - **Property 1: Session Lifecycle Management**
    - **Validates: Requirements 1.1, 1.3, 1.4**

  - [x] 2.3 Implement audio chunk processing and streaming coordination
    - Create AudioChunk value object with 200ms segmentation logic
    - Implement audio stream manager for RTP audio processing
    - Set up gRPC client connections to downstream services
    - _Requirements: 2.1, 2.2_

  - [ ]* 2.4 Write property test for audio streaming pipeline
    - **Property 2: Audio Streaming Pipeline**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4**

- [x] 3. Implement ASR Service with gRPC streaming
  - [x] 3.1 Create ASR Service with bidirectional gRPC streaming
    - Implement gRPC server with ProcessAudioStream method
    - Integrate Vosk ASR plugin for Russian language processing
    - Implement partial and final result generation with confidence scoring
    - Add Voice Activity Detection (VAD) for speech segment detection
    - _Requirements: 3.1, 3.2, 3.3_

  - [ ]* 3.2 Write property test for ASR processing consistency
    - **Property 3: ASR Processing Consistency**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.5**

  - [ ] 3.3 Implement ASR engine fallback and error handling
    - Add Whisper.cpp ASR plugin as fallback option
    - Implement low confidence detection and error recovery
    - Add circuit breaker pattern for ASR engine failures
    - _Requirements: 3.5_

- [ ] 4. Implement NLU Service for intent classification
  - [ ] 4.1 Create NLU Service with intent extraction capabilities
    - Implement gRPC server with ExtractIntent method
    - Integrate spaCy for Russian language processing
    - Create intent classifiers for shopping lists, reminders, and queries
    - Implement entity extraction for items, quantities, and dates
    - _Requirements: 4.1, 4.2, 4.5_

  - [ ]* 4.2 Write property test for intent classification and confidence handling
    - **Property 4: Intent Classification and Confidence Handling**
    - **Validates: Requirements 4.1, 4.2, 4.3, 4.4, 4.5**

  - [ ] 4.3 Implement confidence-based processing logic
    - Add confidence threshold handling (0.7 threshold)
    - Implement high/low confidence routing logic
    - Create error recovery marking for low-confidence results
    - _Requirements: 4.3, 4.4_

- [ ] 5. Checkpoint - Core services integration test
  - Ensure Gateway, ASR, and NLU services communicate correctly
  - Test audio streaming from Gateway to ASR to NLU pipeline
  - Verify session management across service boundaries
  - Ask the user if questions arise

- [ ] 6. Implement Dialog Service for conversation management
  - [ ] 6.1 Create Dialog Service with state management
    - Implement gRPC server with ProcessIntent method
    - Create DialogState entity with conversation history tracking
    - Implement multi-turn conversation logic for shopping lists
    - Add confirmation workflow handling for complex operations
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

  - [ ]* 6.2 Write property test for dialog state management
    - **Property 5: Dialog State Management**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4**

  - [ ] 6.3 Implement dialog error recovery and clarification
    - Add error recovery prompts for low ASR confidence
    - Implement clarifying questions for failed NLU extraction
    - Create help menu and fallback responses
    - _Requirements: 5.5, 9.1, 9.2_

- [ ] 7. Implement TTS Service for speech synthesis
  - [ ] 7.1 Create TTS Service with Russian speech synthesis
    - Implement gRPC server with SynthesizeSpeech method
    - Integrate Silero TTS plugin for Russian language
    - Implement audio streaming back to Gateway Service
    - Add special character and number handling for Russian context
    - _Requirements: 6.1, 6.3, 6.5_

  - [ ]* 7.2 Write property test for speech synthesis pipeline
    - **Property 6: Speech Synthesis Pipeline**
    - **Validates: Requirements 6.1, 6.3, 6.5**

- [ ] 8. Implement Storage Proxy for data persistence
  - [ ] 8.1 Create Storage Proxy with PostgreSQL integration
    - Implement repository pattern for shopping lists and reminders
    - Set up asyncpg connection pooling for optimal performance
    - Create transactional operations for complex data modifications
    - Implement concurrent access handling with proper locking
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ]* 8.2 Write property test for data persistence operations
    - **Property 7: Data Persistence Operations**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5**

- [ ] 9. Implement Notification Worker for async messaging
  - [ ] 9.1 Create Notification Worker with RabbitMQ integration
    - Implement RabbitMQ consumer for notification events
    - Create Telegram bot integration for message delivery
    - Implement retry logic with exponential backoff for API failures
    - Add notification delivery status tracking
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

  - [ ]* 9.2 Write property test for notification event processing
    - **Property 8: Notification Event Processing**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5**

- [ ] 10. Checkpoint - Full service integration test
  - Test complete pipeline: Gateway → ASR → NLU → Dialog → TTS → Gateway
  - Verify Storage Proxy integration with Dialog Service
  - Test Notification Worker with RabbitMQ event publishing
  - Ensure all services handle errors gracefully
  - Ask the user if questions arise
- [ ] 11. Implement FreeSWITCH integration layer
  - [ ] 11.1 Create FreeSWITCH mod_python3 integration module
    - Implement Python module for FreeSWITCH call handling
    - Create SIP call event handlers (incoming call, hangup, etc.)
    - Implement RTP audio streaming to Gateway Service
    - Add call routing and session management integration
    - _Requirements: 1.1, 1.2_

  - [ ] 11.2 Implement Gateway Service HTTP API for FreeSWITCH
    - Create FastAPI endpoints for call control (start, stop, status)
    - Implement audio streaming endpoints for RTP data
    - Add session management API for FreeSWITCH integration
    - Create greeting message playback functionality
    - _Requirements: 1.2, 2.1, 2.2_

- [ ] 12. Implement comprehensive error handling and resilience
  - [ ] 12.1 Add circuit breaker patterns to Gateway Service
    - Implement circuit breakers for all downstream service calls
    - Add timeout handling for unresponsive services
    - Create fallback responses for service failures
    - Implement detailed error logging for debugging
    - _Requirements: 9.3, 9.4, 9.5, 10.4_

  - [ ]* 12.2 Write property test for error recovery and resilience
    - **Property 9: Error Recovery and Resilience**
    - **Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5**

  - [ ] 12.3 Implement service discovery and health checks
    - Add service registration mechanism for all services
    - Implement health check endpoints for monitoring
    - Create service discovery client in Gateway Service
    - Add communication metrics logging for analytics
    - _Requirements: 10.2, 10.3, 10.5_

  - [ ]* 12.4 Write property test for service communication protocol
    - **Property 10: Service Communication Protocol**
    - **Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5**

- [ ] 13. Implement Russian language optimization features
  - [ ] 13.1 Enhance NLU Service for Russian linguistic patterns
    - Add Russian case declension handling in entity extraction
    - Implement Russian-specific intent pattern recognition
    - Create Russian grammar validation for entity processing
    - Add Russian phoneme optimization for ASR integration
    - _Requirements: 12.2, 12.5_

  - [ ] 13.2 Enhance Dialog Service for Russian response generation
    - Implement grammatically correct Russian response templates
    - Add Russian linguistic pattern handling in dialog flow
    - Create Russian-specific confirmation and error messages
    - Implement Russian number and date formatting
    - _Requirements: 12.4, 12.5_

  - [ ]* 13.3 Write property test for Russian language processing
    - **Property 11: Russian Language Processing**
    - **Validates: Requirements 12.2, 12.4, 12.5**

- [ ] 14. Implement Docker containerization and deployment
  - [ ] 14.1 Create Docker images for all services
    - Create multi-stage Dockerfiles for each service
    - Set up base image with Python 3.12+ and dependencies
    - Configure service-specific requirements and plugins
    - Implement health check endpoints in Docker containers
    - _Requirements: Infrastructure setup_

  - [ ] 14.2 Create Docker Compose configuration
    - Set up infrastructure services (PostgreSQL, Redis, RabbitMQ)
    - Configure service networking and communication
    - Add environment variable configuration
    - Create development and production compose files
    - _Requirements: Infrastructure setup_

- [ ] 15. Integration and end-to-end testing
  - [ ] 15.1 Create end-to-end call flow tests
    - Mock FreeSWITCH integration for testing
    - Test complete voice command processing pipelines
    - Verify shopping list and reminder workflows
    - Test notification delivery end-to-end
    - _Requirements: All requirements integration_

  - [ ]* 15.2 Write integration tests for service communication
    - Test Gateway ↔ ASR ↔ NLU ↔ Dialog pipeline
    - Test Storage Proxy ↔ PostgreSQL transactions
    - Test Notification Worker ↔ RabbitMQ ↔ Telegram API
    - _Requirements: Service integration_

  - [ ]* 15.3 Write performance tests for latency requirements
    - Test audio processing latency under 300ms
    - Test intent processing under 100ms
    - Test TTS synthesis under 500ms
    - Test concurrent session handling
    - _Requirements: 2.5, 11.2, 11.3, 11.4_

- [ ] 16. Final checkpoint and system validation
  - Ensure all property-based tests pass with 100+ iterations
  - Verify all services start up and register correctly
  - Test complete call flow from FreeSWITCH to Telegram notification
  - Validate Russian language processing accuracy
  - Confirm error recovery and resilience patterns work correctly
  - Ask the user if questions arise

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Property tests validate universal correctness properties from the design document
- Integration tests ensure service communication works correctly
- Performance tests validate latency requirements for real-time operation
- Russian language optimization is critical for the target use case
- Docker containerization enables scalable deployment