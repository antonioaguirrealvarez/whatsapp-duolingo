"""Integration tests for database schema and models."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.data.models import (
    Base, User, Topic, Exercise, Lesson, LessonExercise, 
    UserProgress, LanguageLevel, ExerciseType, ErrorType
)


class TestDatabaseSchema:
    """Test suite for database schema and models."""
    
    @pytest.fixture
    def engine(self):
        """Create in-memory SQLite engine for testing."""
        return create_engine("sqlite:///:memory:")
    
    @pytest.fixture
    def db_session(self, engine):
        """Create database session with all tables."""
        Base.metadata.create_all(bind=engine)
        with Session(engine) as session:
            yield session
    
    def test_create_user(self, db_session):
        """Test creating a user record."""
        user = User(
            wa_id="1234567890",
            name="Test User",
            phone="+1234567890",
            native_lang="es",
            target_lang="en",
            level=LanguageLevel.A2,
            is_premium=False
        )
        
        db_session.add(user)
        db_session.commit()
        
        # Verify user was created
        retrieved_user = db_session.query(User).filter(User.wa_id == "1234567890").first()
        assert retrieved_user is not None
        assert retrieved_user.name == "Test User"
        assert retrieved_user.native_lang == "es"
        assert retrieved_user.target_lang == "en"
        assert retrieved_user.level == LanguageLevel.A2
        assert retrieved_user.is_premium is False
        assert retrieved_user.daily_lessons_count == 0
        assert retrieved_user.streak_days == 0
    
    def test_create_topic(self, db_session):
        """Test creating a topic record."""
        topic = Topic(
            name="Travel",
            description="Travel-related vocabulary and phrases"
        )
        
        db_session.add(topic)
        db_session.commit()
        
        # Verify topic was created
        retrieved_topic = db_session.query(Topic).filter(Topic.name == "Travel").first()
        assert retrieved_topic is not None
        assert retrieved_topic.description == "Travel-related vocabulary and phrases"
    
    def test_create_exercise(self, db_session):
        """Test creating an exercise record."""
        exercise = Exercise(
            question="How do you say 'hello' in English?",
            correct_answer="Hello",
            options='["Hola", "Hello", "Bonjour", "Ciao"]',
            difficulty=LanguageLevel.A1,
            exercise_type=ExerciseType.MULTIPLE_CHOICE,
            source_lang="es",
            target_lang="en"
        )
        
        db_session.add(exercise)
        db_session.commit()
        
        # Verify exercise was created
        retrieved_exercise = db_session.query(Exercise).filter(Exercise.question == "How do you say 'hello' in English?").first()
        assert retrieved_exercise is not None
        assert retrieved_exercise.correct_answer == "Hello"
        assert retrieved_exercise.difficulty == LanguageLevel.A1
        assert retrieved_exercise.exercise_type == ExerciseType.MULTIPLE_CHOICE
        assert retrieved_exercise.source_lang == "es"
        assert retrieved_exercise.target_lang == "en"
    
    def test_create_lesson(self, db_session, create_test_user):
        """Test creating a lesson record."""
        lesson = Lesson(
            title="Basic Greetings",
            description="Learn basic greeting phrases",
            difficulty=LanguageLevel.A1,
            language_pair="es-en",
            user_id=create_test_user.id
        )
        
        db_session.add(lesson)
        db_session.commit()
        
        # Verify lesson was created
        retrieved_lesson = db_session.query(Lesson).filter(Lesson.title == "Basic Greetings").first()
        assert retrieved_lesson is not None
        assert retrieved_lesson.description == "Learn basic greeting phrases"
        assert retrieved_lesson.difficulty == LanguageLevel.A1
        assert retrieved_lesson.language_pair == "es-en"
        assert retrieved_lesson.is_completed is False
        assert retrieved_lesson.user_id == create_test_user.id
    
    def test_create_lesson_exercise(self, db_session, create_test_lesson, create_test_exercise):
        """Test creating a lesson-exercise junction record."""
        lesson_exercise = LessonExercise(
            order=1,
            lesson_id=create_test_lesson.id,
            exercise_id=create_test_exercise.id,
            is_completed=False,
            user_answer="Hello",
            is_correct=True
        )
        
        db_session.add(lesson_exercise)
        db_session.commit()
        
        # Verify lesson-exercise was created
        retrieved_lesson_exercise = db_session.query(LessonExercise).filter(
            LessonExercise.lesson_id == create_test_lesson.id,
            LessonExercise.exercise_id == create_test_exercise.id
        ).first()
        assert retrieved_lesson_exercise is not None
        assert retrieved_lesson_exercise.order == 1
        assert retrieved_lesson_exercise.is_completed is False
        assert retrieved_lesson_exercise.user_answer == "Hello"
        assert retrieved_lesson_exercise.is_correct is True
    
    def test_create_user_progress(self, db_session, create_test_user, create_test_exercise):
        """Test creating a user progress record."""
        progress = UserProgress(
            user_id=create_test_user.id,
            exercise_id=create_test_exercise.id,
            is_correct=False,
            user_answer="Helo",
            error_type=ErrorType.SPELLING,
            feedback_key="spelling_correction",
            feedback_message="Check your spelling: 'Hello' not 'Helo'",
            response_time_ms=5000,
            attempts=1
        )
        
        db_session.add(progress)
        db_session.commit()
        
        # Verify progress was created
        retrieved_progress = db_session.query(UserProgress).filter(
            UserProgress.user_id == create_test_user.id,
            UserProgress.exercise_id == create_test_exercise.id
        ).first()
        assert retrieved_progress is not None
        assert retrieved_progress.is_correct is False
        assert retrieved_progress.user_answer == "Helo"
        assert retrieved_progress.error_type == ErrorType.SPELLING
        assert retrieved_progress.feedback_key == "spelling_correction"
        assert retrieved_progress.response_time_ms == 5000
        assert retrieved_progress.attempts == 1
    
    def test_relationships(self, db_session):
        """Test model relationships."""
        # Create user
        user = User(wa_id="123", name="Test User", native_lang="es", target_lang="en", level=LanguageLevel.A1)
        db_session.add(user)
        db_session.flush()
        
        # Create topic
        topic = Topic(name="Test Topic")
        db_session.add(topic)
        db_session.flush()
        
        # Create exercise
        exercise = Exercise(
            question="Test question",
            correct_answer="Test answer",
            difficulty=LanguageLevel.A1,
            exercise_type=ExerciseType.TRANSLATION,
            source_lang="es",
            target_lang="en",
            topic_id=topic.id
        )
        db_session.add(exercise)
        db_session.flush()
        
        # Create lesson
        lesson = Lesson(
            title="Test Lesson",
            difficulty=LanguageLevel.A1,
            language_pair="es-en",
            user_id=user.id
        )
        db_session.add(lesson)
        db_session.flush()
        
        # Create lesson-exercise
        lesson_exercise = LessonExercise(
            order=1,
            lesson_id=lesson.id,
            exercise_id=exercise.id
        )
        db_session.add(lesson_exercise)
        db_session.flush()
        
        # Create user progress
        progress = UserProgress(
            user_id=user.id,
            exercise_id=exercise.id,
            is_correct=True,
            user_answer="Test answer"
        )
        db_session.add(progress)
        db_session.commit()
        
        # Test relationships
        assert lesson.user == user
        assert exercise.topic == topic
        assert lesson_exercise.lesson == lesson
        assert lesson_exercise.exercise == exercise
        assert progress.user == user
        assert progress.exercise == exercise
        
        # Test reverse relationships
        assert len(user.lessons) == 1
        assert len(user.user_progress) == 1
        assert len(topic.exercises) == 1
        assert len(lesson.lesson_exercises) == 1
        assert len(exercise.lesson_exercises) == 1
        assert len(exercise.user_progress) == 1
    
    @pytest.fixture
    def create_test_user(self, db_session):
        """Create a test user for use in other tests."""
        user = User(
            wa_id="test_user_123",
            name="Test User",
            native_lang="es",
            target_lang="en",
            level=LanguageLevel.A2
        )
        db_session.add(user)
        db_session.commit()
        return user
    
    @pytest.fixture
    def create_test_topic(self, db_session):
        """Create a test topic for use in other tests."""
        topic = Topic(
            name="Test Topic",
            description="A topic for testing"
        )
        db_session.add(topic)
        db_session.commit()
        return topic
    
    @pytest.fixture
    def create_test_exercise(self, db_session, create_test_topic):
        """Create a test exercise for use in other tests."""
        exercise = Exercise(
            question="Test question?",
            correct_answer="Test answer",
            difficulty=LanguageLevel.A1,
            exercise_type=ExerciseType.MULTIPLE_CHOICE,
            source_lang="es",
            target_lang="en",
            topic_id=create_test_topic.id
        )
        db_session.add(exercise)
        db_session.commit()
        return exercise
    
    @pytest.fixture
    def create_test_lesson(self, db_session, create_test_user):
        """Create a test lesson for use in other tests."""
        lesson = Lesson(
            title="Test Lesson",
            description="A lesson for testing",
            difficulty=LanguageLevel.A1,
            language_pair="es-en",
            user_id=create_test_user.id
        )
        db_session.add(lesson)
        db_session.commit()
        return lesson
