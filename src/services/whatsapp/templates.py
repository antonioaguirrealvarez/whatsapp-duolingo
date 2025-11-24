"""WhatsApp message templates and formatting utilities."""

import logging
from typing import Any, Dict, List, Optional

from src.services.whatsapp.utils import handle_emoji

logger = logging.getLogger(__name__)


class MessageTemplates:
    """Pre-defined message templates for common interactions."""
    
    @staticmethod
    def welcome_message(user_name: Optional[str] = None) -> str:
        """
        Generate welcome message.
        
        Args:
            user_name: Optional user name for personalization
            
        Returns:
            Welcome message text
        """
        if user_name:
            return handle_emoji(f"¡Hola {user_name}! 👋\n\nWelcome to your AI Language Tutor! I'm here to help you learn languages through fun, interactive conversations right here on WhatsApp.\n\nReady to start learning? 🚀")
        else:
            return handle_emoji("¡Hola! 👋\n\nWelcome to your AI Language Tutor! I'm here to help you learn languages through fun, interactive conversations right here on WhatsApp.\n\nReady to start learning? 🚀")
    
    @staticmethod
    def level_selection_menu() -> str:
        """
        Generate language level selection menu.
        
        Returns:
            Level selection message
        """
        return handle_emoji(
            "📚 **Choose Your Level**\n\n"
            "What's your current level in the language you want to learn?\n\n"
            "1. 🌱 **Beginner (A1)** - Just starting out\n"
            "2. 🌿 **Elementary (A2)** - Basic phrases\n"
            "3. 🌳 **Intermediate (B1)** - Conversational\n"
            "4. 🌲 **Upper-Intermediate (B2)** - Confident\n"
            "5. 🌴 **Advanced (C1)** - Fluent\n"
            "6. 🌺 **Mastery (C2)** - Native-like\n\n"
            "Reply with the number of your choice!"
        )
    
    @staticmethod
    def language_selection_menu() -> str:
        """
        Generate language selection menu.
        
        Returns:
            Language selection message
        """
        return handle_emoji(
            "🌍 **What language do you want to learn?**\n\n"
            "1. 🇺🇸 **English** - Learn English\n"
            "2. 🇫🇷 **French** - Learn French\n"
            "3. 🇮🇹 **Italian** - Learn Italian\n"
            "4. 🇩🇪 **German** - Learn German\n\n"
            "Reply with the number of your choice!"
        )
    
    @staticmethod
    def daily_limit_message() -> str:
        """
        Generate daily limit reached message.
        
        Returns:
            Daily limit message
        """
        return handle_emoji(
            "🔥 You're on fire today! 🎉\n\n"
            "You've completed your free lesson for today. Want to keep going?\n\n"
            "💎 **Upgrade to Pro** for unlimited lessons, voice practice, and advanced features!\n\n"
            "📱 [Upgrade Now](https://your-domain.com/upgrade)\n"
            "💰 Only $9/month • Cancel anytime\n\n"
            "Or come back tomorrow for your next free lesson! 🌅"
        )
    
    @staticmethod
    def progress_update(
        streak: int,
        lessons_completed: int,
        current_level: str
    ) -> str:
        """
        Generate progress update message.
        
        Args:
            streak: Current streak in days
            lessons_completed: Total lessons completed
            current_level: Current user level
            
        Returns:
            Progress update message
        """
        return handle_emoji(
            f"📊 **Your Progress** 📊\n\n"
            f"🔥 **Streak**: {streak} days\n"
            f"📚 **Lessons**: {lessons_completed} completed\n"
            f"🎯 **Level**: {current_level}\n\n"
            f"Keep up the great work! 💪"
        )
    
    @staticmethod
    def lesson_prompt(
        topic: str,
        difficulty: str,
        question: str
    ) -> str:
        """
        Generate lesson question prompt.
        
        Args:
            topic: Lesson topic
            difficulty: Difficulty level
            question: The question text
            
        Returns:
            Lesson prompt message
        """
        return handle_emoji(
            f"📖 **{topic}** ({difficulty})\n\n"
            f"{question}\n\n"
            f"Type your answer below or type 'help' for a hint! 💡"
        )
    
    @staticmethod
    def format_multiple_choice(question: str, options: List[str]) -> str:
        """
        Format a multiple choice question.
        
        Args:
            question: The question text
            options: List of option strings
            
        Returns:
            Formatted multiple choice question
        """
        formatted = handle_emoji(f"📝 **Question:**\n{question}\n\n")
        formatted += "**Choose the correct option:**\n"
        
        for i, option in enumerate(options, 1):
            formatted += f"{i}. {option}\n"
        
        formatted += "\nReply with the number of your choice! 🎯"
        
        return formatted
    
    @staticmethod
    def correct_answer_feedback(
        answer: str,
        explanation: Optional[str] = None
    ) -> str:
        """
        Generate correct answer feedback.
        
        Args:
            answer: User's correct answer
            explanation: Optional explanation
            
        Returns:
            Correct answer feedback
        """
        base_feedback = handle_emoji(f"✅ **Correct!** Well done! 🎉\n\nYour answer: {answer}")
        
        if explanation:
            base_feedback += f"\n\n💡 **Why it's correct**: {explanation}"
        
        base_feedback += "\n\nReady for the next question? 🚀"
        
        return base_feedback
    
    @staticmethod
    def incorrect_answer_feedback(
        answer: str,
        correct_answer: str,
        explanation: str
    ) -> str:
        """
        Generate incorrect answer feedback.
        
        Args:
            answer: User's incorrect answer
            correct_answer: The correct answer
            explanation: Explanation of why it's incorrect
            
        Returns:
            Incorrect answer feedback
        """
        return handle_emoji(
            f"❌ **Not quite right** 😅\n\n"
            f"Your answer: {answer}\n"
            f"Correct answer: {correct_answer}\n\n"
            f"💡 **Here's why**: {explanation}\n\n"
            f"Don't worry, practice makes perfect! Want to try another? 🌟"
        )
    
    @staticmethod
    def help_menu() -> str:
        """
        Generate help menu.
        
        Returns:
            Help menu message
        """
        return handle_emoji(
            "🤖 **AI Language Tutor Help** 🤖\n\n"
            "**Available Commands:**\n\n"
            "• **menu** - Show main menu\n"
            "• **progress** - Check your progress\n"
            "• **streak** - View your streak\n"
            "• **help** - Show this help menu\n"
            "• **stop** - End current lesson\n\n"
            "**Features:**\n"
            "• 🎯 Personalized lessons\n"
            "• 🔥 Daily streaks\n"
            "• 📊 Progress tracking\n"
            "• 💬 Interactive practice\n\n"
            "Need more help? Just ask! 🌟"
        )
    
    @staticmethod
    def goodbye_message() -> str:
        """
        Generate goodbye message.
        
        Returns:
            Goodbye message
        """
        return handle_emoji(
            "👋 **Goodbye for now!**\n\n"
            "Great job today! Come back tomorrow to continue your learning journey.\n\n"
            "Remember: consistency is key to mastering a new language! 🌟\n\n"
            "See you soon! 🚀"
        )


class InteractiveTemplates:
    """Templates for interactive WhatsApp elements."""
    
    @staticmethod
    def create_button_response(
        text: str,
        buttons: List[str]
    ) -> Dict[str, Any]:
        """
        Create a button response structure.
        
        Args:
            text: Message text
            buttons: List of button texts
            
        Returns:
            Button response structure
        """
        return {
            "type": "buttons",
            "text": text,
            "buttons": [
                {"id": f"btn_{i+1}", "text": button}
                for i, button in enumerate(buttons)
            ]
        }
    
    @staticmethod
    def create_list_response(
        header: str,
        rows: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Create a list response structure.
        
        Args:
            header: List header
            rows: List of rows with id and title
            
        Returns:
            List response structure
        """
        return {
            "type": "list",
            "header": header,
            "rows": [
                {"id": row["id"], "title": row["title"]}
                for row in rows
            ]
        }
    
    @staticmethod
    def format_multiple_choice(
        question: str,
        options: List[str]
    ) -> str:
        """
        Format multiple choice question.
        
        Args:
            question: Question text
            options: List of options
            
        Returns:
            Formatted multiple choice question
        """
        formatted_options = "\n".join([
            f"{chr(65+i)}. {option}"  # A, B, C, etc.
            for i, option in enumerate(options)
        ])
        
        return handle_emoji(
            f"❓ **Question**\n\n"
            f"{question}\n\n"
            f"{formatted_options}\n\n"
            f"Reply with the letter of your choice (A, B, C, etc.)"
        )
    
    @staticmethod
    def format_fill_in_blank(
        sentence: str,
        blank_word: str
    ) -> str:
        """
        Format fill-in-the-blank exercise.
        
        Args:
            sentence: Sentence with blank
            blank_word: The word that should fill the blank
            
        Returns:
            Formatted fill-in-the-blank exercise
        """
        return handle_emoji(
            f"✍️ **Fill in the Blank**\n\n"
            f"Complete the sentence:\n\n"
            f"{sentence}\n\n"
            f"Type your answer below! 💭"
        )
