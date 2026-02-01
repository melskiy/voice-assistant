"""
Add Shopping Item Command Handler.

User goal: Add an item to the shopping list.
Success guarantee: Item is added to the list.
Side effects: Creates or updates shopping list in repository.
"""
from uuid import UUID

from ...domain.entities.shopping_list import ShoppingList, ShoppingItem
from ...domain.repositories.shopping_repository import IShoppingRepository
from ...domain.repositories.session_repository import ISessionRepository
from ..commands.add_shopping_item_command import AddShoppingItemCommand
from ..dto.command_result import CommandResult


class AddShoppingItemHandler:
    """
    Handler for AddShoppingItemCommand.
    
    Processes the command and returns a result.
    """
    
    def __init__(
        self,
        shopping_repo: IShoppingRepository,
        session_repo: ISessionRepository
    ):
        self.shopping_repo = shopping_repo
        self.session_repo = session_repo
    
    async def handle(self, command: AddShoppingItemCommand) -> CommandResult:
        """
        Handle the command.
        
        Args:
            command: AddShoppingItemCommand with item details
            
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
            
            # Get or create shopping list for session
            shopping_list = await self.shopping_repo.get_by_session(command.session_id)
            
            if not shopping_list:
                shopping_list = ShoppingList.create(command.session_id)
            
            # Create and add item
            item = ShoppingItem(
                name=command.item_name,
                quantity=command.quantity,
                unit=command.unit,
                priority=command.priority
            )
            
            shopping_list.add_item(item)
            
            # Save updated list
            await self.shopping_repo.save(shopping_list)
            
            return CommandResult.success(
                message=f"Добавлено {command.item_name} в список покупок",
                data={
                    "item_name": command.item_name,
                    "list_id": str(shopping_list.id)
                }
            )
            
        except Exception as e:
            return CommandResult.failure(
                message=f"Ошибка при добавлении товара: {str(e)}",
                error_code="ADD_ITEM_ERROR"
            )
