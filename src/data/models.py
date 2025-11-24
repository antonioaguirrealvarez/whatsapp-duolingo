"""Database models for WhatsApp Duolingo application."""

from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

import enum

Base = declarative_base()


class LanguageLevel(enum.Enum):
    """CEFR language levels."""
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class ExerciseType(enum.Enum):
    """Types of exercises."""
    MULTIPLE_CHOICE = "multiple_choice"
    FILL_IN_BLANK = "fill_in_blank"
    TRANSLATION = "translation"
    LISTENING = "listening"
    SPEAKING = "speaking"
    ROLEPLAY = "roleplay"


class ErrorType(enum.Enum):
    """Types of errors in user responses."""
    GRAMMAR = "grammar"
    VOCABULARY = "vocabulary"
    SPELLING = "spelling"
    SYNTAX = "syntax"
    COMPREHENSION = "comprehension"
    NONE = "none"


class User(Base):
    """User model representing a WhatsApp user."""
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    wa_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(100))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    
    # Learning preferences
    native_lang: Mapped[Optional[str]] = mapped_column(String(10))  # e.g., "es", "pt"
    target_lang: Mapped[Optional[str]] = mapped_column(String(10))  # e.g., "en", "fr"
    level: Mapped[Optional[LanguageLevel]] = mapped_column(SQLEnum(LanguageLevel))
    
    # Business logic
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    daily_lessons_count: Mapped[int] = mapped_column(Integer, default=0)
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    last_lesson_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    user_progress: Mapped[list["UserProgress"]] = relationship("UserProgress", back_populates="user")
    lessons: Mapped[list["Lesson"]] = relationship("Lesson", back_populates="user")


class Topic(Base):
    """Topic model for categorizing exercises."""
    __tablename__ = "topics"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    exercises: Mapped[list["Exercise"]] = relationship("Exercise", back_populates="topic")


class Exercise(Base):
    """Exercise model representing individual learning items."""
    __tablename__ = "exercises"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Content
    question: Mapped[str] = mapped_column(Text, nullable=False)
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[Optional[str]] = mapped_column(Text)  # JSON string for multiple choice
    
    # Classification
    difficulty: Mapped[LanguageLevel] = mapped_column(SQLEnum(LanguageLevel), nullable=False)
    exercise_type: Mapped[ExerciseType] = mapped_column(SQLEnum(ExerciseType), nullable=False)
    
    # Language pair
    source_lang: Mapped[str] = mapped_column(String(10), nullable=False)  # e.g., "es"
    target_lang: Mapped[str] = mapped_column(String(10), nullable=False)  # e.g., "en"
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Foreign keys
    topic_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("topics.id"))
    
    # Relationships
    topic: Mapped[Optional["Topic"]] = relationship("Topic", back_populates="exercises")
    user_progress: Mapped[list["UserProgress"]] = relationship("UserProgress", back_populates="exercise")
    lesson_exercises: Mapped[list["LessonExercise"]] = relationship("LessonExercise", back_populates="exercise")


class Lesson(Base):
    """Lesson model representing a collection of exercises."""
    __tablename__ = "lessons"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Lesson info
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    
    # Classification
    difficulty: Mapped[LanguageLevel] = mapped_column(SQLEnum(LanguageLevel), nullable=False)
    language_pair: Mapped[str] = mapped_column(String(25), nullable=False)  # e.g., "es-en"
    
    # Status
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Foreign keys
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="lessons")
    lesson_exercises: Mapped[list["LessonExercise"]] = relationship("LessonExercise", back_populates="lesson")


class LessonExercise(Base):
    """Junction table for lessons and exercises with order."""
    __tablename__ = "lesson_exercises"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Order in lesson
    order: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Status
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    user_answer: Mapped[Optional[str]] = mapped_column(Text)
    is_correct: Mapped[Optional[bool]] = mapped_column(Boolean)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Foreign keys
    lesson_id: Mapped[int] = mapped_column(Integer, ForeignKey("lessons.id"), nullable=False)
    exercise_id: Mapped[int] = mapped_column(Integer, ForeignKey("exercises.id"), nullable=False)
    
    # Relationships
    lesson: Mapped["Lesson"] = relationship("Lesson", back_populates="lesson_exercises")
    exercise: Mapped["Exercise"] = relationship("Exercise", back_populates="lesson_exercises")


class UserProgress(Base):
    """User progress tracking for individual exercises."""
    __tablename__ = "user_progress"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Performance
    is_correct: Mapped[bool] = mapped_column(Boolean, nullable=False)
    user_answer: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Error analysis
    error_type: Mapped[Optional[ErrorType]] = mapped_column(SQLEnum(ErrorType))
    feedback_key: Mapped[Optional[str]] = mapped_column(String(100))  # e.g., "verb_conjugation"
    feedback_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Metrics
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer)  # Time taken to answer
    attempts: Mapped[int] = mapped_column(Integer, default=1)  # Number of attempts
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
    
    # Foreign keys
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    exercise_id: Mapped[int] = mapped_column(Integer, ForeignKey("exercises.id"), nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="user_progress")
    exercise: Mapped["Exercise"] = relationship("Exercise", back_populates="user_progress")


class EvaluationLog(Base):
    """Log of LLM evaluations for quality tracking."""
    __tablename__ = "evaluation_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Evaluation type
    evaluation_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "correctness", "tone"
    
    # Input/Output
    input_data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    output_data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    
    # Metrics
    confidence_score: Mapped[Optional[float]] = mapped_column(Integer)  # 0.0-1.0
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    
    # Foreign keys
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"))


class ContentGenerationLog(Base):
    """Log of content generation for tracking and debugging."""
    __tablename__ = "content_generation_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    
    # Generation parameters
    source_lang: Mapped[str] = mapped_column(String(10), nullable=False)
    target_lang: Mapped[str] = mapped_column(String(10), nullable=False)
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    level: Mapped[LanguageLevel] = mapped_column(SQLEnum(LanguageLevel), nullable=False)
    exercise_type: Mapped[ExerciseType] = mapped_column(SQLEnum(ExerciseType), nullable=False)
    count: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Results
    generated_count: Mapped[int] = mapped_column(Integer, nullable=False)
    accepted_count: Mapped[int] = mapped_column(Integer, nullable=False)
    
    # Status
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # "success", "partial", "failed"
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    # Metrics
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    
    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
