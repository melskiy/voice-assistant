"""
Create Reminder Command Handler.

User goal: Create a new reminder.
Success guarantee: Reminder is created and scheduled.
Side effects: Saves reminder to repository.
"""
from ...domain.entities.reminder import Reminder
from ...domain.repositories.reminder_repository import IReminderRepository
from ...domain.repositories.session_repository import ISessionRepository
from ..commands.create_reminder_command import CreateReminderCommand
from ..dto.command_result import CommandResult


class CreateReminderHandler:
    """
    Handler for CreateReminderCommand.
    
    Processes the command and returns a result.
    """
    
    def __init__(
        self,
        reminder_repo: IReminderRepository,
        session_repo: ISessionRepository
    ):
        self.reminder_repo = reminder_repo
        self.session_repo = session_repo
    
    async def handle(self, command: CreateReminderCommand) -> CommandResult:
        """
        Handle the command.
        
        Args:
            command: CreateReminderCommand with reminder details
            
        Returns:
            CommandResult indicating success or failure
        """
        try:
            # Verify session exists
            session = await self.session_repo.get_by_id(command.session_id)
            if not session:
                return CommandResult.failure(
                    message="Сессия не найдена",
                    error_code="SESSION_NOT_FOUND"
                )
            
            # Create reminder
            reminder = Reminder.create(
                session_id=command.session_id,
                description=command.description,
                reminder_date=command.reminder_date,
                location=command.location,
                repeat_interval=command.repeat_interval
            )
            
            # Save reminder
            await self.reminder_repo.save(reminder)
            
            return CommandResult.success(
                message=f"Напоминание создано: {command.description}",
                data={
                    "reminder_id": str(reminder.id),
                    "description": command.description,
                    "date": command.reminder_date.isoformat()
                }
            )
            
        except Exception as e:
            return CommandResult.failure(
                message=f"Ошибка при создании напоминания: {str(e)}",
                error_code="CREATE_REMINDER_ERROR"
            )
