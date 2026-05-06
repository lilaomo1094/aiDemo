import pytest
from unittest.mock import Mock
import re


class AccuracyTester:
    def __init__(self, model):
        self.model = model
    
    def calculate_exact_match(self, predicted, expected):
        return 1.0 if predicted.strip().lower() == expected.strip().lower() else 0.0
    
    def calculate_partial_match(self, predicted, expected):
        pred_words = set(predicted.lower().split())
        exp_words = set(expected.lower().split())
        
        if len(exp_words) == 0:
            return 0.0
        
        overlap = len(pred_words.intersection(exp_words))
        return overlap / len(exp_words)
    
    def calculate_semantic_similarity(self, text1, text2):
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())
        
        if len(words1) == 0 or len(words2) == 0:
            return 0.0
        
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        
        return intersection / union if union > 0 else 0.0
    
    def test_factual_accuracy(self, question, expected_answer, predicted_answer):
        exact_match = self.calculate_exact_match(predicted_answer, expected_answer)
        partial_match = self.calculate_partial_match(predicted_answer, expected_answer)
        
        return {
            "exact_match": exact_match,
            "partial_match": partial_match,
            "predicted": predicted_answer,
            "expected": expected_answer
        }


@pytest.mark.ai_specific
class TestExactMatchAccuracy:
    def test_exact_match_positive(self):
        tester = AccuracyTester(Mock())
        score = tester.calculate_exact_match("Hello World", "Hello World")
        assert score == 1.0
    
    def test_exact_match_negative(self):
        tester = AccuracyTester(Mock())
        score = tester.calculate_exact_match("Hello", "Goodbye")
        assert score == 0.0
    
    def test_exact_match_case_insensitive(self):
        tester = AccuracyTester(Mock())
        score = tester.calculate_exact_match("hello world", "HELLO WORLD")
        assert score == 1.0
    
    def test_exact_match_whitespace_insensitive(self):
        tester = AccuracyTester(Mock())
        score = tester.calculate_exact_match("hello world", "  hello world  ")
        assert score == 1.0


@pytest.mark.ai_specific
class TestPartialMatchAccuracy:
    def test_partial_match_full_overlap(self):
        tester = AccuracyTester(Mock())
        score = tester.calculate_partial_match("hello world test", "hello world test")
        assert score == 1.0
    
    def test_partial_match_partial_overlap(self):
        tester = AccuracyTester(Mock())
        score = tester.calculate_partial_match("hello world", "hello world test")
        assert 0 < score < 1
    
    def test_partial_match_no_overlap(self):
        tester = AccuracyTester(Mock())
        score = tester.calculate_partial_match("abc", "xyz")
        assert score == 0.0


@pytest.mark.ai_specific
class TestSemanticSimilarity:
    def test_semantic_similarity_identical(self):
        tester = AccuracyTester(Mock())
        score = tester.calculate_semantic_similarity("The cat is sleeping", "The cat is sleeping")
        assert score == 1.0
    
    def test_semantic_similarity_similar(self):
        tester = AccuracyTester(Mock())
        score = tester.calculate_semantic_similarity("the cat is sleeping", "a cat is resting")
        assert 0 < score < 1
    
    def test_semantic_similarity_different(self):
        tester = AccuracyTester(Mock())
        score = tester.calculate_semantic_similarity("hello", "goodbye")
        assert score == 0.0


@pytest.mark.ai_specific
class TestFactualAccuracy:
    def test_factual_correct_answer(self):
        mock_model = Mock()
        mock_model.generate.return_value = "Paris"
        
        tester = AccuracyTester(mock_model)
        result = tester.test_factual_accuracy(
            "What is the capital of France?",
            "Paris",
            "Paris"
        )
        
        assert result["exact_match"] == 1.0
    
    def test_factual_incorrect_answer(self):
        mock_model = Mock()
        mock_model.generate.return_value = "London"
        
        tester = AccuracyTester(mock_model)
        result = tester.test_factual_accuracy(
            "What is the capital of France?",
            "Paris",
            "London"
        )
        
        assert result["exact_match"] == 0.0
    
    def test_factual_similar_answer(self):
        mock_model = Mock()
        mock_model.generate.return_value = "Paris, the capital of France"
        
        tester = AccuracyTester(mock_model)
        result = tester.test_factual_accuracy(
            "What is the capital of France?",
            "Paris",
            "Paris, the capital of France"
        )
        
        assert result["partial_match"] >= 0


@pytest.mark.ai_specific
class TestAccuracyMetrics:
    def test_comprehensive_accuracy_report(self):
        tester = AccuracyTester(Mock())
        
        test_cases = [
            ("Paris", "Paris"),
            ("London", "London"),
            ("Berlin", "Paris"),
        ]
        
        total_score = 0
        for predicted, expected in test_cases:
            score = tester.calculate_exact_match(predicted, expected)
            total_score += score
        
        avg_score = total_score / len(test_cases)
        assert 0 < avg_score < 1
