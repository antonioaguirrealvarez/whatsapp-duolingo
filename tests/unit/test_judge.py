"""Unit tests for the correctness evaluator."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.llm.evals.judge_correctness import CorrectnessEvaluator


class TestCorrectnessEvaluator:
    """Test suite for the CorrectnessEvaluator class."""
    
    @pytest.fixture
    def mock_model(self):
        """Create a mock OpenAI model."""
        model = MagicMock()
        return model
    
    @pytest.fixture
    def evaluator(self, mock_model):
        """Create evaluator with mocked model and chain."""
        with patch('src.services.llm.evals.judge_correctness.ChatOpenAI', return_value=mock_model):
            eval_instance = CorrectnessEvaluator(model=mock_model)
            # Mock the chain as a regular object
            eval_instance.chain = MagicMock()
            return eval_instance
    
    @pytest.mark.asyncio
    async def test_evaluate_correct_response(self, evaluator):
        """Test evaluation of a correct response."""
        # Mock the chain to return a correct evaluation
        mock_result = {
            "is_correct": True,
            "error_type": None,
            "feedback_key": None,
            "confidence": 0.95,
            "explanation": "Perfect response!"
        }
        evaluator.chain.ainvoke = AsyncMock(return_value=mock_result)
        
        result = await evaluator.evaluate_response(
            question="What is 'hello' in Spanish?",
            user_answer="Hola",
            rubric="translation"
        )
        
        assert result["is_correct"] is True
        assert result["error_type"] is None
        assert result["feedback_key"] is None
        assert result["confidence"] == 0.95
        assert "Perfect" in result["explanation"]
    
    @pytest.mark.asyncio
    async def test_evaluate_grammar_error(self, evaluator):
        """Test evaluation of a response with grammar errors."""
        mock_result = {
            "is_correct": False,
            "error_type": "grammar",
            "feedback_key": "verb_conjugation",
            "confidence": 0.88,
            "explanation": "Wrong verb conjugation used"
        }
        evaluator.chain.ainvoke = AsyncMock(return_value=mock_result)
        
        result = await evaluator.evaluate_response(
            question="Conjugate 'to be' for 'I am happy'",
            user_answer="I be happy",
            rubric="verb conjugation"
        )
        
        assert result["is_correct"] is False
        assert result["error_type"] == "grammar"
        assert result["feedback_key"] == "verb_conjugation"
        assert result["confidence"] == 0.88
    
    @pytest.mark.asyncio
    async def test_evaluate_spelling_error(self, evaluator):
        """Test evaluation of a response with spelling errors."""
        mock_result = {
            "is_correct": False,
            "error_type": "spelling",
            "feedback_key": "spelling_correction",
            "confidence": 0.92,
            "explanation": "Spelling mistake detected"
        }
        evaluator.chain.ainvoke = AsyncMock(return_value=mock_result)
        
        result = await evaluator.evaluate_response(
            question="How do you spell 'restaurant'?",
            user_answer="resturant",
            rubric="spelling"
        )
        
        assert result["is_correct"] is False
        assert result["error_type"] == "spelling"
        assert result["feedback_key"] == "spelling_correction"
    
    @pytest.mark.asyncio
    async def test_evaluate_vocabulary_error(self, evaluator):
        """Test evaluation of a response with vocabulary errors."""
        mock_result = {
            "is_correct": False,
            "error_type": "vocabulary",
            "feedback_key": "word_choice",
            "confidence": 0.85,
            "explanation": "Incorrect word choice"
        }
        evaluator.chain.ainvoke = AsyncMock(return_value=mock_result)
        
        result = await evaluator.evaluate_response(
            question="What's a synonym for 'big'?",
            user_answer="small",  # This is an antonym, not synonym
            rubric="vocabulary"
        )
        
        assert result["is_correct"] is False
        assert result["error_type"] == "vocabulary"
        assert result["feedback_key"] == "word_choice"
    
    @pytest.mark.asyncio
    async def test_evaluation_with_invalid_json(self, evaluator):
        """Test handling of invalid JSON from LLM."""
        # Mock the chain to return invalid JSON (string instead of dict)
        evaluator.chain.ainvoke = AsyncMock(return_value="invalid json response")
        
        result = await evaluator.evaluate_response(
            question="Test question",
            user_answer="Test answer",
            rubric="test"
        )
        
        # Should return fallback evaluation
        assert result["is_correct"] is False
        assert result["error_type"] == "comprehension"
        assert result["feedback_key"] == "evaluation_error"
        assert result["confidence"] == 0.0
    
    @pytest.mark.asyncio
    async def test_evaluation_with_exception(self, evaluator):
        """Test handling of exceptions during evaluation."""
        # Mock the chain to raise an exception
        evaluator.chain.ainvoke = AsyncMock(side_effect=Exception("API Error"))
        
        result = await evaluator.evaluate_response(
            question="Test question",
            user_answer="Test answer",
            rubric="test"
        )
        
        # Should return fallback evaluation
        assert result["is_correct"] is False
        assert result["error_type"] == "comprehension"
        assert result["feedback_key"] == "evaluation_error"
        assert result["confidence"] == 0.0
    
    @pytest.mark.asyncio
    async def test_batch_evaluation(self, evaluator):
        """Test batch evaluation of multiple responses."""
        # Mock individual evaluations
        evaluator.evaluate_response = AsyncMock(side_effect=[
            {"is_correct": True, "error_type": None, "feedback_key": None, "confidence": 0.9, "explanation": "Good"},
            {"is_correct": False, "error_type": "grammar", "feedback_key": "verb", "confidence": 0.8, "explanation": "Bad"},
            {"is_correct": True, "error_type": None, "feedback_key": None, "confidence": 0.95, "explanation": "Great"},
        ])
        
        responses = [
            {"question": "Q1", "user_answer": "A1", "rubric": "test"},
            {"question": "Q2", "user_answer": "A2", "rubric": "test"},
            {"question": "Q3", "user_answer": "A3", "rubric": "test"},
        ]
        
        results = await evaluator.batch_evaluate(responses)
        
        assert len(results) == 3
        assert results[0]["is_correct"] is True
        assert results[1]["is_correct"] is False
        assert results[2]["is_correct"] is True
    
    def test_fallback_evaluation_structure(self, evaluator):
        """Test that fallback evaluation has the correct structure."""
        fallback = evaluator._get_fallback_evaluation()
        
        required_keys = ["is_correct", "error_type", "feedback_key", "confidence", "explanation"]
        for key in required_keys:
            assert key in fallback
        
        assert fallback["is_correct"] is False
        assert fallback["confidence"] == 0.0
