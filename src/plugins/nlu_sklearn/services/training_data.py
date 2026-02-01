"""
Training data provider for Scikit-learn NLU.
"""

from typing import List, Tuple

from ..interfaces import ITrainingDataProvider


class DefaultTrainingDataProvider(ITrainingDataProvider):
    """
    Default training data provider with built-in samples.
    
    Provides training data for common voice assistant intents.
    """
    
    def __init__(self, language: str = "ru"):
        """
        Initialize provider.
        
        Args:
            language: Language code (ru, en)
        """
        self.language = language
    
    def get_training_data(self) -> List[Tuple[str, str]]:
        """
        Get training data as list of (text, label) tuples.
        
        Returns:
            List of training samples
        """
        if self.language == "ru":
            return self._get_russian_training_data()
        else:
            return self._get_english_training_data()
    
    def get_intent_labels(self) -> List[str]:
        """Get list of all intent labels."""
        return [
            "ADD_SHOPPING_ITEM",
            "REMOVE_SHOPPING_ITEM",
            "GET_SHOPPING_LIST",
            "CREATE_REMINDER",
            "GET_REMINDERS",
            "CONFIRM_YES",
            "CONFIRM_NO",
            "UNKNOWN"
        ]
    
    def _get_russian_training_data(self) -> List[Tuple[str, str]]:
        """Get Russian training data."""
        return [
            # ADD_SHOPPING_ITEM
            ("добавь молоко в список", "ADD_SHOPPING_ITEM"),
            ("купи хлеб", "ADD_SHOPPING_ITEM"),
            ("нужен сахар", "ADD_SHOPPING_ITEM"),
            ("возьми масло", "ADD_SHOPPING_ITEM"),
            ("положи яйца в список", "ADD_SHOPPING_ITEM"),
            ("добавь сыр", "ADD_SHOPPING_ITEM"),
            ("купи колбасу", "ADD_SHOPPING_ITEM"),
            ("нужна мука", "ADD_SHOPPING_ITEM"),
            ("в список добавь чай", "ADD_SHOPPING_ITEM"),
            ("запиши кофе", "ADD_SHOPPING_ITEM"),
            
            # REMOVE_SHOPPING_ITEM
            ("удали молоко из списка", "REMOVE_SHOPPING_ITEM"),
            ("убери хлеб", "REMOVE_SHOPPING_ITEM"),
            ("вычеркни сахар", "REMOVE_SHOPPING_ITEM"),
            ("не нужен масло", "REMOVE_SHOPPING_ITEM"),
            ("удали яйца", "REMOVE_SHOPPING_ITEM"),
            ("убери сыр из списка", "REMOVE_SHOPPING_ITEM"),
            ("вычеркни колбасу", "REMOVE_SHOPPING_ITEM"),
            ("не нужна мука", "REMOVE_SHOPPING_ITEM"),
            
            # GET_SHOPPING_LIST
            ("покажи список покупок", "GET_SHOPPING_LIST"),
            ("что в списке", "GET_SHOPPING_LIST"),
            ("список покупок", "GET_SHOPPING_LIST"),
            ("перечисли что купить", "GET_SHOPPING_LIST"),
            ("что нужно купить", "GET_SHOPPING_LIST"),
            ("покажи что в списке", "GET_SHOPPING_LIST"),
            ("назови покупки", "GET_SHOPPING_LIST"),
            ("что записано в список", "GET_SHOPPING_LIST"),
            
            # CREATE_REMINDER
            ("напомни купить молоко", "CREATE_REMINDER"),
            ("установи напоминание", "CREATE_REMINDER"),
            ("запомни позвонить", "CREATE_REMINDER"),
            ("напомни завтра", "CREATE_REMINDER"),
            ("установи напоминание на вечер", "CREATE_REMINDER"),
            ("запомни сходить в магазин", "CREATE_REMINDER"),
            ("напомни про встречу", "CREATE_REMINDER"),
            ("создай напоминание", "CREATE_REMINDER"),
            
            # GET_REMINDERS
            ("какие напоминания", "GET_REMINDERS"),
            ("покажи напоминания", "GET_REMINDERS"),
            ("что запланировано", "GET_REMINDERS"),
            ("какие у меня напоминания", "GET_REMINDERS"),
            ("перечисли напоминания", "GET_REMINDERS"),
            ("что я просил напомнить", "GET_REMINDERS"),
            
            # CONFIRM_YES
            ("да", "CONFIRM_YES"),
            ("да, верно", "CONFIRM_YES"),
            ("верно", "CONFIRM_YES"),
            ("правильно", "CONFIRM_YES"),
            ("так", "CONFIRM_YES"),
            ("да, так", "CONFIRM_YES"),
            ("конечно", "CONFIRM_YES"),
            ("да, пожалуйста", "CONFIRM_YES"),
            
            # CONFIRM_NO
            ("нет", "CONFIRM_NO"),
            ("нет, неправильно", "CONFIRM_NO"),
            ("не верно", "CONFIRM_NO"),
            ("неправильно", "CONFIRM_NO"),
            ("отмена", "CONFIRM_NO"),
            ("отменить", "CONFIRM_NO"),
            ("нет, спасибо", "CONFIRM_NO"),
            ("не надо", "CONFIRM_NO"),
        ]
    
    def _get_english_training_data(self) -> List[Tuple[str, str]]:
        """Get English training data."""
        return [
            # ADD_SHOPPING_ITEM
            ("add milk to the list", "ADD_SHOPPING_ITEM"),
            ("buy bread", "ADD_SHOPPING_ITEM"),
            ("need sugar", "ADD_SHOPPING_ITEM"),
            ("get butter", "ADD_SHOPPING_ITEM"),
            ("put eggs on the list", "ADD_SHOPPING_ITEM"),
            ("add cheese", "ADD_SHOPPING_ITEM"),
            ("buy sausage", "ADD_SHOPPING_ITEM"),
            ("need flour", "ADD_SHOPPING_ITEM"),
            ("add tea to shopping list", "ADD_SHOPPING_ITEM"),
            ("write down coffee", "ADD_SHOPPING_ITEM"),
            
            # REMOVE_SHOPPING_ITEM
            ("remove milk from the list", "REMOVE_SHOPPING_ITEM"),
            ("take off bread", "REMOVE_SHOPPING_ITEM"),
            ("delete sugar", "REMOVE_SHOPPING_ITEM"),
            ("don't need butter", "REMOVE_SHOPPING_ITEM"),
            ("remove eggs", "REMOVE_SHOPPING_ITEM"),
            ("take cheese off the list", "REMOVE_SHOPPING_ITEM"),
            ("delete sausage", "REMOVE_SHOPPING_ITEM"),
            ("don't need flour", "REMOVE_SHOPPING_ITEM"),
            
            # GET_SHOPPING_LIST
            ("show shopping list", "GET_SHOPPING_LIST"),
            ("what's on the list", "GET_SHOPPING_LIST"),
            ("shopping list", "GET_SHOPPING_LIST"),
            ("list what to buy", "GET_SHOPPING_LIST"),
            ("what do I need to buy", "GET_SHOPPING_LIST"),
            ("show what's on the list", "GET_SHOPPING_LIST"),
            ("name the items", "GET_SHOPPING_LIST"),
            ("what's recorded in the list", "GET_SHOPPING_LIST"),
            
            # CREATE_REMINDER
            ("remind me to buy milk", "CREATE_REMINDER"),
            ("set a reminder", "CREATE_REMINDER"),
            ("remember to call", "CREATE_REMINDER"),
            ("remind me tomorrow", "CREATE_REMINDER"),
            ("set reminder for evening", "CREATE_REMINDER"),
            ("remember to go to store", "CREATE_REMINDER"),
            ("remind me about meeting", "CREATE_REMINDER"),
            ("create a reminder", "CREATE_REMINDER"),
            
            # GET_REMINDERS
            ("what reminders do I have", "GET_REMINDERS"),
            ("show reminders", "GET_REMINDERS"),
            ("what's planned", "GET_REMINDERS"),
            ("what are my reminders", "GET_REMINDERS"),
            ("list reminders", "GET_REMINDERS"),
            ("what did I ask to be reminded", "GET_REMINDERS"),
            
            # CONFIRM_YES
            ("yes", "CONFIRM_YES"),
            ("yes, correct", "CONFIRM_YES"),
            ("correct", "CONFIRM_YES"),
            ("right", "CONFIRM_YES"),
            ("that's right", "CONFIRM_YES"),
            ("yes, that's it", "CONFIRM_YES"),
            ("sure", "CONFIRM_YES"),
            ("yes, please", "CONFIRM_YES"),
            
            # CONFIRM_NO
            ("no", "CONFIRM_NO"),
            ("no, incorrect", "CONFIRM_NO"),
            ("not correct", "CONFIRM_NO"),
            ("incorrect", "CONFIRM_NO"),
            ("cancel", "CONFIRM_NO"),
            ("cancel it", "CONFIRM_NO"),
            ("no, thanks", "CONFIRM_NO"),
            ("don't need it", "CONFIRM_NO"),
        ]
