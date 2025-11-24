"""Unit tests for the tone evaluator."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.llm.evals.judge_tone import ToneEvaluator


class TestToneEvaluator:
    """Test suite for the ToneEvaluator class."""
    
    @pytest.fixture
    def mock_model(self):
        """Create a mock OpenAI model."""
        model = MagicMock()
        return model
    
    @pytest.fixture
    def evaluator(self, mock_model):
        """Create evaluator with mocked model and chain."""
        with patch('src.services.llm.evals.judge_tone.ChatOpenAI', return_value=mock_model):
            eval_instance = ToneEvaluator(model=mock_model)
            # Mock the chain as a regular object
            eval_instance.chain = MagicMock()
            return eval_instance
    
    @pytest.mark.asyncio
    async def test_assess_engaging_response(self, evaluator):
        """Test assessment of an engaging, viral response."""
        mock_result = {
            "virality_score": 9.2,
            "personality_score": 8.8,
            "engagement_score": 9.5,
            "is_boring": False,
            "feedback": "Excellent! Very engaging and fun personality.",
            "improvement_suggestions": None
        }
        evaluator.chain.ainvoke = AsyncMock(return_value=mock_result)
        
        result = await evaluator.assess_virality(
            bot_response="¡Hola! 🌟 Ready to rock some Spanish? Let's make this fun! 😎"
        )
        
        assert result["virality_score"] == 9.2
        assert result["personality_score"] == 8.8
        assert result["engagement_score"] == 9.5
        assert result["is_boring"] is False
        assert "Excellent" in result["feedback"]
        assert result["improvement_suggestions"] is None
    
    @pytest.mark.asyncio
    async def test_assess_boring_response(self, evaluator):
        """Test assessment of a boring, dry response."""
        mock_result = {
            "virality_score": 3.1,
            "personality_score": 2.8,
            "engagement_score": 3.5,
            "is_boring": True,
            "feedback": "Very boring and dry. Needs more personality.",
            "improvement_suggestions": "Add emojis, slang, and more enthusiastic tone"
        }
        evaluator.chain.ainvoke = AsyncMock(return_value=mock_result)
        
        result = await evaluator.assess_virality(
            bot_response="The answer is blue. Please study more."
        )
        
        assert result["virality_score"] == 3.1
        assert result["is_boring"] is True
        assert "boring" in result["feedback"].lower()
        assert "emojis" in result["improvement_suggestions"]
    
    @pytest.mark.asyncio
    async def test_should_regenerate_boring_response(self, evaluator):
        """Test that boring responses should be regenerated."""
        mock_result = {
            "virality_score": 4.5,
            "personality_score": 5.0,
            "engagement_score": 4.0,
            "is_boring": True,
            "feedback": "Below average engagement",
            "improvement_suggestions": "Add more personality"
        }
        evaluator.chain.ainvoke = AsyncMock(return_value=mock_result)
        
        should_regenerate, evaluation = await evaluator.should_regenerate(
            bot_response="This is the correct answer.",
            threshold=7.0
        )
        
        assert should_regenerate is True
        assert evaluation["virality_score"] == 4.5
        assert evaluation["is_boring"] is True
    
    @pytest.mark.asyncio
    async def test_should_not_regenerate_engaging_response(self, evaluator):
        """Test that engaging responses should not be regenerated."""
        mock_result = {
            "virality_score": 8.7,
            "personality_score": 9.0,
            "engagement_score": 8.5,
            "is_boring": False,
            "feedback": "Great engaging response",
            "improvement_suggestions": None
        }
        evaluator.chain.ainvoke = AsyncMock(return_value=mock_result)
        
        should_regenerate, evaluation = await evaluator.should_regenerate(
            bot_response="¡Awesome work! 🎉 You're killing it! Let's keep this energy going!",
            threshold=7.0
        )
        
        assert should_regenerate is False
        assert evaluation["virality_score"] == 8.7
        assert evaluation["is_boring"] is False
    
    @pytest.mark.asyncio
    async def test_suggest_improvements_for_boring_response(self, evaluator):
        """Test getting improvement suggestions for boring responses."""
        mock_result = {
            "virality_score": 4.2,
            "personality_score": 3.8,
            "engagement_score": 4.5,
            "is_boring": True,
            "feedback": "Response needs more energy",
            "improvement_suggestions": "Add emojis, use slang like 'qué onda', and be more enthusiastic"
        }
        evaluator.chain.ainvoke = AsyncMock(return_value=mock_result)
        
        suggestions = await evaluator.suggest_improvements(
            bot_response="The answer is correct."
        )
        
        assert suggestions is not None
        assert "emojis" in suggestions
        assert "qué onda" in suggestions
    
    @pytest.mark.asyncio
    async def test_suggest_improvements_for_good_response(self, evaluator):
        """Test that good responses return None for improvements."""
        mock_result = {
            "virality_score": 8.9,
            "personality_score": 9.2,
            "engagement_score": 8.7,
            "is_boring": False,
            "feedback": "Excellent engaging response",
            "improvement_suggestions": None
        }
        evaluator.chain.ainvoke = AsyncMock(return_value=mock_result)
        
        suggestions = await evaluator.suggest_improvements(
            bot_response="¡Qué bueno! 🎊 You're absolutely crushing it! Keep that energy!"
        )
        
        assert suggestions is None
    
    @pytest.mark.asyncio
    async def test_assessment_with_invalid_json(self, evaluator):
        """Test handling of invalid JSON from LLM."""
        evaluator.chain.ainvoke = AsyncMock(return_value="invalid json response")
        
        result = await evaluator.assess_virality("Test response")
        
        # Should return fallback evaluation
        assert result["virality_score"] == 5.0
        assert result["is_boring"] is True
        assert "error" in result["feedback"].lower()
    
    @pytest.mark.asyncio
    async def test_assessment_with_exception(self, evaluator):
        """Test handling of exceptions during assessment."""
        evaluator.chain.ainvoke = AsyncMock(side_effect=Exception("API Error"))
        
        result = await evaluator.assess_virality("Test response")
        
        # Should return fallback evaluation
        assert result["virality_score"] == 5.0
        assert result["is_boring"] is True
        assert "error" in result["feedback"].lower()
    
    @pytest.mark.asyncio
    async def test_batch_assessment(self, evaluator):
        """Test batch assessment of multiple responses."""
        evaluator.assess_virality = AsyncMock(side_effect=[
            {"virality_score": 8.5, "is_boring": False, "feedback": "Good", "personality_score": 8.0, "engagement_score": 9.0, "improvement_suggestions": None},
            {"virality_score": 4.2, "is_boring": True, "feedback": "Boring", "personality_score": 4.0, "engagement_score": 4.5, "improvement_suggestions": "Add emojis"},
            {"virality_score": 9.1, "is_boring": False, "feedback": "Great", "personality_score": 9.5, "engagement_score": 8.8, "improvement_suggestions": None},
        ])
        
        responses = [
            "Great response! 🎉",
            "Boring response.",
            "Amazing! Let's go! 🔥"
        ]
        
        results = await evaluator.batch_assess(responses)
        
        assert len(results) == 3
        assert results[0]["virality_score"] == 8.5
        assert results[1]["is_boring"] is True
        assert results[2]["virality_score"] == 9.1
    
    def test_fallback_evaluation_structure(self, evaluator):
        """Test that fallback evaluation has the correct structure."""
        fallback = evaluator._get_fallback_evaluation()
        
        required_keys = ["virality_score", "personality_score", "engagement_score", "is_boring", "feedback", "improvement_suggestions"]
        for key in required_keys:
            assert key in fallback
        
        assert fallback["virality_score"] == 5.0
        assert fallback["is_boring"] is True
        assert fallback["personality_score"] == 5.0
        assert fallback["engagement_score"] == 5.0
    
    @pytest.mark.asyncio
    async def test_missing_fields_handling(self, evaluator):
        """Test handling of missing fields in evaluation result."""
        mock_result = {
            "virality_score": 8.5,
            # Missing other fields
        }
        evaluator.chain.ainvoke = AsyncMock(return_value=mock_result)
        
        result = await evaluator.assess_virality("Test response")
        
        # Should fill in missing fields
        assert result["virality_score"] == 8.5
        assert result["personality_score"] == 5.0
        assert result["engagement_score"] == 5.0
        assert result["feedback"] is None
        assert result["is_boring"] is False  # Based on virality_score > 7.0
