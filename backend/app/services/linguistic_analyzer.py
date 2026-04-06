"""
Linguistic Analysis for AI-Generated Text Detection
"""

import re
import logging
from typing import Dict, List
from collections import Counter

logger = logging.getLogger(__name__)

try:
    import nltk
    NLTK_AVAILABLE = True
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt', quiet=True)
except ImportError:
    NLTK_AVAILABLE = False
    logger.warning("NLTK not available - using basic analysis")

try:
    import textstat
    TEXTSTAT_AVAILABLE = True
except ImportError:
    TEXTSTAT_AVAILABLE = False
    logger.warning("textstat not available")

try:
    from app.config import authenticity_config as config
except ImportError:
    class FallbackConfig:
        AI_SIGNATURE_PHRASES = ["first and foremost", "it's important to note"]
        FILLER_WORDS = ["um", "uh", "like"]
    config = FallbackConfig()


class LinguisticAnalyzer:
    """Analyzes text for AI-generated patterns"""
    
    def __init__(self):
        self.ai_phrases = getattr(config, 'AI_SIGNATURE_PHRASES', [])
        self.filler_words = getattr(config, 'FILLER_WORDS', [])
    
    def analyze_text(self, text: str) -> Dict:
        if not text or len(text) < 10:
            return self._empty_result()
        
        try:
            text_lower = text.lower()
            
            if NLTK_AVAILABLE:
                words = nltk.word_tokenize(text_lower)
                sentences = nltk.sent_tokenize(text)
            else:
                words = text_lower.split()
                sentences = [s.strip() for s in text.split('.') if s.strip()]
            
            filler_ratio = self._calculate_filler_ratio(words)
            ai_phrase_count = self._detect_ai_phrases(text_lower)
            formality_score = self._calculate_formality(text, words)
            structure_score = self._analyze_structure(sentences)
            
            ai_likelihood = self._calculate_ai_likelihood(
                filler_ratio, ai_phrase_count, formality_score, structure_score
            )
            
            return {
                "word_count": len(words),
                "sentence_count": len(sentences),
                "filler_ratio": round(filler_ratio, 4),
                "ai_phrase_count": ai_phrase_count,
                "ai_phrases_detected": self._get_detected_phrases(text_lower),
                "formality_score": round(formality_score, 3),
                "structure_score": round(structure_score, 3),
                "ai_likelihood": round(ai_likelihood, 3),
                "is_likely_ai": ai_likelihood > 0.6,
                "confidence": self._calculate_confidence(text, words)
            }
        except Exception as e:
            logger.error(f"Linguistic analysis error: {e}", exc_info=True)
            return self._empty_result()
    
    def _calculate_filler_ratio(self, words: List[str]) -> float:
        if not words:
            return 0.0
        filler_count = sum(1 for word in words if word in self.filler_words)
        return filler_count / len(words)
    
    def _detect_ai_phrases(self, text: str) -> int:
        count = 0
        for phrase in self.ai_phrases:
            count += text.count(phrase)
        return count
    
    def _get_detected_phrases(self, text: str) -> List[str]:
        detected = []
        for phrase in self.ai_phrases:
            if phrase in text:
                detected.append(phrase)
        return detected[:5]
    
    def _calculate_formality(self, text: str, words: List[str]) -> float:
        if not words:
            return 0.5
        
        formal_words = ['furthermore', 'moreover', 'subsequently', 'therefore']
        informal_contractions = ["'ll", "'re", "'ve", "'d", "n't"]
        
        formal_count = sum(1 for word in words if word in formal_words)
        informal_count = sum(1 for word in words if any(c in word for c in informal_contractions))
        
        if formal_count + informal_count == 0:
            return 0.5
        
        formality = formal_count / (formal_count + informal_count + 1)
        
        if TEXTSTAT_AVAILABLE:
            try:
                reading_ease = textstat.flesch_reading_ease(text)
                complexity_factor = max(0, (100 - reading_ease) / 100)
                formality = (formality + complexity_factor) / 2
            except:
                pass
        
        return min(formality, 1.0)
    
    def _analyze_structure(self, sentences: List[str]) -> float:
        if len(sentences) < 3:
            return 0.5
        
        lengths = [len(s.split()) for s in sentences]
        avg_length = sum(lengths) / len(lengths)
        variance = sum((l - avg_length) ** 2 for l in lengths) / len(lengths)
        
        structure_score = 1.0 - min(variance / 50, 1.0)
        return structure_score
    
    def _calculate_ai_likelihood(self, filler_ratio: float, ai_phrase_count: int,
                                 formality: float, structure: float) -> float:
        filler_score = 1.0 - min(filler_ratio / 0.05, 1.0)
        phrase_score = min(ai_phrase_count / 3, 1.0)
        
        ai_likelihood = (
            filler_score * 0.3 +
            phrase_score * 0.3 +
            formality * 0.25 +
            structure * 0.15
        )
        
        return min(ai_likelihood, 1.0)
    
    def _calculate_confidence(self, text: str, words: List[str]) -> float:
        word_count = len(words)
        if word_count < 20:
            return 0.3
        elif word_count < 50:
            return 0.6
        elif word_count < 100:
            return 0.8
        else:
            return 0.95
    
    def _empty_result(self) -> Dict:
        return {
            "word_count": 0,
            "sentence_count": 0,
            "filler_ratio": 0.0,
            "ai_phrase_count": 0,
            "ai_phrases_detected": [],
            "formality_score": 0.0,
            "structure_score": 0.0,
            "ai_likelihood": 0.0,
            "is_likely_ai": False,
            "confidence": 0.0
        }


_linguistic_analyzer = None

def get_linguistic_analyzer() -> LinguisticAnalyzer:
    global _linguistic_analyzer
    if _linguistic_analyzer is None:
        _linguistic_analyzer = LinguisticAnalyzer()
        logger.info("✅ Linguistic analyzer initialized")
    return _linguistic_analyzer