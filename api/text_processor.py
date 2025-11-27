import random


class TextProcessor:
    """Class to handle text processing logic"""
    
    def __init__(self):
        self.random_endings = [
            " ...and that's awesome! 🎉",
            " ...how interesting! 🤔",
            " ...that's amazing! ✨",
            " ...wonderful choice! 🌟",
            " ...I love it! ❤️",
            " ...that's fantastic! 🚀",
            " ...brilliant! 💎",
            " ...spectacular! 🎊",
            " ...mind-blowing! 🤯",
            " ...keep it up! 💪"
        ]
    
    def process_text(self, text: str) -> str:
        """
        Takes a string and returns it with a random ending appended.
        
        Args:
            text (str): The input text to process
            
        Returns:
            str: The processed text with a random ending
        """
        random_ending = random.choice(self.random_endings)
        return text + random_ending
