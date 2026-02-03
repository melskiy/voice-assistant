"""
Text Normalizer domain service.

Business concept: Normalizes text for TTS synthesis.
Handles Russian language specifics.
"""
import re
from typing import Dict, List


class RussianTextNormalizer:
    """
    Domain service for Russian text normalization.
    
    Handles:
    - Number-to-word conversion
    - Abbreviation expansion
    - Special character normalization
    """
    
    # Russian number words
    ONES = ['', 'один', 'два', 'три', 'четыре', 'пять', 'шесть', 'семь', 'восемь', 'девять']
    TEENS = ['десять', 'одиннадцать', 'двенадцать', 'тринадцать', 'четырнадцать',
             'пятнадцать', 'шестнадцать', 'семнадцать', 'восемнадцать', 'девятнадцать']
    TENS = ['', '', 'двадцать', 'тридцать', 'сорок', 'пятьдесят',
            'шестьдесят', 'семьдесят', 'восемьдесят', 'девяносто']
    HUNDREDS = ['', 'сто', 'двести', 'триста', 'четыреста', 'пятьсот',
                'шестьсот', 'семьсот', 'восемьсот', 'девятьсот']
    THOUSANDS = ['', 'тысяча', 'тысячи', 'тысяч']
    MILLIONS = ['', 'миллион', 'миллиона', 'миллионов']
    
    ABBREVIATIONS: Dict[str, str] = {
        'т.д.': 'так далее',
        'т.е.': 'то есть',
        'и т.п.': 'и тому подобное',
        'др.': 'другой',
        'г.': 'год',
        'гг.': 'годы',
        'ул.': 'улица',
        'пр.': 'проспект',
        'кв.': 'квартира',
        'кг': 'килограмм',
        'км': 'километр',
        'м': 'метр',
        'см': 'сантиметр',
        'мм': 'миллиметр',
        'л': 'литр',
        'мл': 'миллилитр',
        'ч': 'час',
        'мин': 'минута',
        'сек': 'секунда',
        'руб': 'рубль',
        'долл': 'доллар',
        'евро': 'евро',
    }
    
    @classmethod
    def normalize(cls, text: str) -> str:
        """
        Normalize text for TTS.
        
        Args:
            text: Input text
            
        Returns:
            Normalized text
        """
        if not text:
            return text
        
        # Expand abbreviations
        text = cls._expand_abbreviations(text)
        
        # Convert numbers
        text = cls._convert_numbers(text)
        
        # Normalize special characters
        text = cls._normalize_special_chars(text)
        
        # Clean whitespace
        text = ' '.join(text.split())
        
        return text
    
    @classmethod
    def _expand_abbreviations(cls, text: str) -> str:
        """Expand abbreviations."""
        for abbrev, expansion in cls.ABBREVIATIONS.items():
            text = text.replace(abbrev, expansion)
            text = text.replace(abbrev.upper(), expansion)
        return text
    
    @classmethod
    def _convert_numbers(cls, text: str) -> str:
        """Convert numbers to words."""
        numbers = re.findall(r'\b\d+\b', text)
        
        for num_str in numbers:
            try:
                num = int(num_str)
                if 0 <= num <= 999999999:
                    word = cls._number_to_words(num)
                    text = text.replace(num_str, word, 1)
            except ValueError:
                continue
        
        return text
    
    @classmethod
    def _number_to_words(cls, num: int) -> str:
        """Convert number to Russian words."""
        if num == 0:
            return 'ноль'
        
        if num < 0:
            return 'минус ' + cls._number_to_words(-num)
        
        parts = []
        
        # Millions
        if num >= 1000000:
            millions = num // 1000000
            parts.append(cls._number_to_words(millions))
            parts.append(cls._get_million_form(millions))
            num %= 1000000
        
        # Thousands
        if num >= 1000:
            thousands = num // 1000
            parts.append(cls._number_to_words_thousands(thousands))
            parts.append(cls._get_thousand_form(thousands))
            num %= 1000
        
        # Hundreds, tens, ones
        if num > 0:
            parts.append(cls._number_to_words_small(num))
        
        return ' '.join(parts)
    
    @classmethod
    def _number_to_words_thousands(cls, num: int) -> str:
        """Convert thousands with feminine form."""
        if num == 1:
            return 'одна'
        elif num == 2:
            return 'две'
        else:
            return cls._number_to_words_small(num)
    
    @classmethod
    def _number_to_words_small(cls, num: int) -> str:
        """Convert numbers 1-999."""
        parts = []
        
        # Hundreds
        if num >= 100:
            parts.append(cls.HUNDREDS[num // 100])
            num %= 100
        
        # Tens and teens
        if num >= 20:
            parts.append(cls.TENS[num // 10])
            num %= 10
        elif num >= 10:
            parts.append(cls.TEENS[num - 10])
            num = 0
        
        # Ones
        if num > 0:
            parts.append(cls.ONES[num])
        
        return ' '.join(parts)
    
    @classmethod
    def _get_thousand_form(cls, num: int) -> str:
        """Get correct form of 'thousand'."""
        if 11 <= num % 100 <= 14:
            return cls.THOUSANDS[3]
        last_digit = num % 10
        if last_digit == 1:
            return cls.THOUSANDS[1]
        elif 2 <= last_digit <= 4:
            return cls.THOUSANDS[2]
        else:
            return cls.THOUSANDS[3]
    
    @classmethod
    def _get_million_form(cls, num: int) -> str:
        """Get correct form of 'million'."""
        if 11 <= num % 100 <= 14:
            return cls.MILLIONS[3]
        last_digit = num % 10
        if last_digit == 1:
            return cls.MILLIONS[1]
        elif 2 <= last_digit <= 4:
            return cls.MILLIONS[2]
        else:
            return cls.MILLIONS[3]
    
    @classmethod
    def _normalize_special_chars(cls, text: str) -> str:
        """Normalize special characters."""
        replacements = {
            '%': ' процент',
            '°': ' градус',
            '€': ' евро',
            '$': ' доллар',
            '£': ' фунт',
            '+': ' плюс ',
            '=': ' равно ',
            '×': ' умножить на ',
            '÷': ' разделить на ',
            '@': ' собака ',
            '#': ' номер ',
            '&': ' и ',
        }
        
        for char, word in replacements.items():
            text = text.replace(char, word)
        
        # Remove other special characters
        text = re.sub(r'[^\w\s\-\.\,\!\?\(\)\[\]"\'а-яА-ЯёЁ]', ' ', text)
        
        return text
