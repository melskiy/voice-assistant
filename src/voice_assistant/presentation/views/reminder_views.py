"""
Reminder views for Gateway Service.
"""
import logging
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import Request, HTTPException, Query

from .base import BaseViewSet, viewset
from ..schemas import (
    ReminderCreateRequest,
    ReminderResponse,
    ReminderListResponse,
    ReminderUpdateRequest,
    ReminderDeleteResponse,
)
from voice_assistant.domain.entities.reminder import Reminder

logger = logging.getLogger(__name__)


@viewset("reminders", "/reminders")
class ReminderViewSet(BaseViewSet):
    """
    ViewSet for reminder management endpoints.
    Handles CRUD operations for reminders.
    """
    
    tags = ["Reminders"]
    
    def _register_routes(self) -> None:
        """Register reminder routes"""
        # Reminder CRUD
        self.router.add_api_route(
            "/{session_id}",
            self.get_reminders,
            methods=["GET"],
            response_model=ReminderListResponse,
            summary="Get reminders",
            description="Get all reminders for a session",
        )
        
        self.router.add_api_route(
            "/{session_id}",
            self.create_reminder,
            methods=["POST"],
            response_model=ReminderResponse,
            summary="Create reminder",
            description="Create a new reminder for the session",
        )
        
        self.router.add_api_route(
            "/{session_id}/{reminder_id}",
            self.get_reminder,
            methods=["GET"],
            response_model=ReminderResponse,
            summary="Get reminder",
            description="Get a specific reminder by ID",
        )
        
        self.router.add_api_route(
            "/{session_id}/{reminder_id}",
            self.update_reminder,
            methods=["PUT"],
            response_model=ReminderResponse,
            summary="Update reminder",
            description="Update an existing reminder",
        )
        
        self.router.add_api_route(
            "/{session_id}/{reminder_id}",
            self.delete_reminder,
            methods=["DELETE"],
            response_model=ReminderDeleteResponse,
            summary="Delete reminder",
            description="Delete a reminder",
        )
        
        # Bulk operations
        self.router.add_api_route(
            "/{session_id}/clear",
            self.clear_reminders,
            methods=["POST"],
            response_model=ReminderListResponse,
            summary="Clear reminders",
            description="Clear all or completed reminders for the session",
        )

    def _get_reminder_repository(self, request: Request):
        """Get reminder repository from dependencies"""
        repo = self.get_dependency("reminder_repository")
        if repo is None:
            # Try to get from app state
            repo = self.get_state_attr(request, "reminder_repository")
        return repo

    def _reminder_to_response(self, reminder: Reminder) -> ReminderResponse:
        """Convert Reminder domain entity to response schema"""
        now = datetime.utcnow()
        
        # Calculate is_overdue and is_upcoming
        is_overdue = reminder.reminder_date < now and not reminder.notified
        time_until = reminder.reminder_date - now
        is_upcoming = timedelta(0) < time_until <= timedelta(hours=1) and not reminder.notified
        
        return ReminderResponse(
            id=str(reminder.id),
            session_id=str(reminder.session_id),
            description=reminder.description,
            reminder_date=reminder.reminder_date,
            location=reminder.location,
            repeat_interval=reminder.repeat_interval,
            created_at=reminder.created_at,
            notified=reminder.notified,
            is_overdue=is_overdue,
            is_upcoming=is_upcoming
        )

    async def get_reminders(
        self,
        session_id: str,
        request: Request,
        include_completed: bool = Query(False, description="Include completed/notified reminders"),
        upcoming_only: bool = Query(False, description="Show only upcoming reminders (next 24 hours)"),
        overdue_only: bool = Query(False, description="Show only overdue reminders")
    ) -> ReminderListResponse:
        """
        Get reminders for a session.
        
        Args:
            session_id: Session ID
            request: FastAPI request object
            include_completed: Whether to include completed reminders
            upcoming_only: Show only upcoming reminders
            overdue_only: Show only overdue reminders
            
        Returns:
            ReminderListResponse with reminders
        """
        try:
            # Validate session ID
            session_uuid = UUID(session_id)
            
            # Get repository
            repository = self._get_reminder_repository(request)
            
            if repository:
                # Use repository if available
                reminders = await repository.get_by_session_id(session_uuid)
            else:
                # Fallback: return empty list
                logger.warning(f"No reminder repository available, returning empty list for {session_id}")
                reminders = []
            
            # Convert to response objects
            reminder_responses = [self._reminder_to_response(r) for r in reminders]
            
            # Apply filters
            if not include_completed:
                reminder_responses = [r for r in reminder_responses if not r.notified]
            
            if upcoming_only:
                reminder_responses = [r for r in reminder_responses if r.is_upcoming]
            
            if overdue_only:
                reminder_responses = [r for r in reminder_responses if r.is_overdue]
            
            # Sort by reminder date
            reminder_responses.sort(key=lambda x: x.reminder_date)
            
            # Count statistics
            overdue_count = sum(1 for r in reminder_responses if r.is_overdue)
            upcoming_count = sum(1 for r in reminder_responses if r.is_upcoming)
            
            return ReminderListResponse(
                session_id=session_id,
                reminders=reminder_responses,
                total_count=len(reminder_responses),
                overdue_count=overdue_count,
                upcoming_count=upcoming_count
            )
            
        except ValueError:
            raise self.handle_error("Invalid session ID format", status_code=400)
        except Exception as e:
            logger.error(f"Error getting reminders: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)

    async def create_reminder(
        self,
        session_id: str,
        request_data: ReminderCreateRequest,
        request: Request
    ) -> ReminderResponse:
        """
        Create a new reminder.
        
        Args:
            session_id: Session ID
            request_data: Reminder creation request
            request: FastAPI request object
            
        Returns:
            ReminderResponse with created reminder
        """
        try:
            # Validate session ID
            session_uuid = UUID(session_id)
            
            # Create domain entity
            reminder = Reminder.create(
                session_id=session_uuid,
                description=request_data.description,
                reminder_date=request_data.reminder_date,
                location=request_data.location,
                repeat_interval=request_data.repeat_interval
            )
            
            # Get repository
            repository = self._get_reminder_repository(request)
            
            if repository:
                # Save to repository
                await repository.save(reminder)
                logger.info(f"Created reminder for session {session_id}: {reminder.description[:50]}")
            else:
                logger.warning(f"No reminder repository available, reminder not persisted: {reminder.description[:50]}")
            
            return self._reminder_to_response(reminder)
            
        except ValueError as e:
            if "Invalid session ID" in str(e):
                raise self.handle_error("Invalid session ID format", status_code=400)
            raise self.handle_error(str(e), status_code=400)
        except Exception as e:
            logger.error(f"Error creating reminder: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)

    async def get_reminder(
        self,
        session_id: str,
        reminder_id: str,
        request: Request
    ) -> ReminderResponse:
        """
        Get a specific reminder.
        
        Args:
            session_id: Session ID
            reminder_id: Reminder ID
            request: FastAPI request object
            
        Returns:
            ReminderResponse with reminder details
        """
        try:
            session_uuid = UUID(session_id)
            reminder_uuid = UUID(reminder_id)
            
            repository = self._get_reminder_repository(request)
            
            if not repository:
                raise self.handle_error("Reminder repository not available", status_code=503)
            
            # Get reminder
            reminder = await repository.get_by_id(reminder_uuid)
            
            if not reminder:
                raise self.handle_error("Reminder not found", status_code=404)
            
            # Verify it belongs to the session
            if reminder.session_id != session_uuid:
                raise self.handle_error("Reminder does not belong to this session", status_code=403)
            
            return self._reminder_to_response(reminder)
            
        except ValueError:
            raise self.handle_error("Invalid ID format", status_code=400)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting reminder: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)

    async def update_reminder(
        self,
        session_id: str,
        reminder_id: str,
        request_data: ReminderUpdateRequest,
        request: Request
    ) -> ReminderResponse:
        """
        Update a reminder.
        
        Args:
            session_id: Session ID
            reminder_id: Reminder ID
            request_data: Update request
            request: FastAPI request object
            
        Returns:
            ReminderResponse with updated reminder
        """
        try:
            session_uuid = UUID(session_id)
            reminder_uuid = UUID(reminder_id)
            
            repository = self._get_reminder_repository(request)
            
            if not repository:
                raise self.handle_error("Reminder repository not available", status_code=503)
            
            # Get existing reminder
            reminder = await repository.get_by_id(reminder_uuid)
            
            if not reminder:
                raise self.handle_error("Reminder not found", status_code=404)
            
            # Verify it belongs to the session
            if reminder.session_id != session_uuid:
                raise self.handle_error("Reminder does not belong to this session", status_code=403)
            
            # Update fields
            if request_data.description is not None:
                reminder.description = request_data.description
            if request_data.reminder_date is not None:
                reminder.reminder_date = request_data.reminder_date
            if request_data.location is not None:
                reminder.location = request_data.location
            if request_data.repeat_interval is not None:
                reminder.repeat_interval = request_data.repeat_interval
            if request_data.notified is not None:
                if request_data.notified:
                    reminder.mark_as_notified()
                else:
                    reminder.notified = False
            
            # Save updated reminder
            await repository.save(reminder)
            
            logger.info(f"Updated reminder {reminder_id} in session {session_id}")
            
            return self._reminder_to_response(reminder)
            
        except ValueError:
            raise self.handle_error("Invalid ID format", status_code=400)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating reminder: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)

    async def delete_reminder(
        self,
        session_id: str,
        reminder_id: str,
        request: Request
    ) -> ReminderDeleteResponse:
        """
        Delete a reminder.
        
        Args:
            session_id: Session ID
            reminder_id: Reminder ID
            request: FastAPI request object
            
        Returns:
            ReminderDeleteResponse with result
        """
        try:
            session_uuid = UUID(session_id)
            reminder_uuid = UUID(reminder_id)
            
            repository = self._get_reminder_repository(request)
            
            if not repository:
                raise self.handle_error("Reminder repository not available", status_code=503)
            
            # Verify reminder exists and belongs to session
            reminder = await repository.get_by_id(reminder_uuid)
            if not reminder:
                raise self.handle_error("Reminder not found", status_code=404)
            
            if reminder.session_id != session_uuid:
                raise self.handle_error("Reminder does not belong to this session", status_code=403)
            
            # Delete reminder
            success = await repository.delete(reminder_uuid)
            
            if not success:
                raise self.handle_error("Failed to delete reminder", status_code=500)
            
            logger.info(f"Deleted reminder {reminder_id} from session {session_id}")
            
            return ReminderDeleteResponse(
                success=True,
                message="Reminder deleted successfully",
                deleted_reminder_id=reminder_id
            )
            
        except ValueError:
            raise self.handle_error("Invalid ID format", status_code=400)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting reminder: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)

    async def clear_reminders(
        self,
        session_id: str,
        request: Request,
        only_notified: bool = Query(True, description="Clear only notified/completed reminders")
    ) -> ReminderListResponse:
        """
        Clear reminders for a session.
        
        Args:
            session_id: Session ID
            request: FastAPI request object
            only_notified: Whether to clear only notified reminders
            
        Returns:
            ReminderListResponse with updated list
        """
        try:
            session_uuid = UUID(session_id)
            
            repository = self._get_reminder_repository(request)
            
            if repository:
                if only_notified:
                    await repository.delete_notified_by_session(session_uuid)
                else:
                    await repository.delete_all_by_session(session_uuid)
                
                logger.info(f"Cleared reminders for session {session_id} (only_notified={only_notified})")
            else:
                logger.warning(f"No reminder repository available for clearing reminders {session_id}")
            
            # Return empty list
            return ReminderListResponse(
                session_id=session_id,
                reminders=[],
                total_count=0,
                overdue_count=0,
                upcoming_count=0
            )
            
        except ValueError:
            raise self.handle_error("Invalid session ID format", status_code=400)
        except Exception as e:
            logger.error(f"Error clearing reminders: {e}", exc_info=True)
            raise self.handle_error(str(e), status_code=500)