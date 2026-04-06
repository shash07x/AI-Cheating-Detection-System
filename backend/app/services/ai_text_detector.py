"""
AI Text Detector - Google Gemini + Heuristic Analysis

Pipeline:
  Transcript text → Gemini AI Analysis → AI vs Human score
  Fallback: Transcript text → Heuristic Analysis → AI vs Human score

Detects whether spoken words (transcribed to text) were likely:
  - Read from an AI assistant (ChatGPT, Gemini, Claude, etc.)
  - Genuinely human-generated speech

This works like a plagiarism detector for AI-generated content.
"""

import os
import logging
import time
import threading
from typing import Dict, List, Tuple
from collections import deque

logger = logging.getLogger(__name__)

# ================================================
# GEMINI CONFIGURATION
# ================================================

GEMINI_AVAILABLE = False
_gemini_model = None
_gemini_lock = threading.Lock()

# Rate limiting for Gemini API
_last_gemini_call = 0
GEMINI_COOLDOWN = 10.0  # seconds between API calls (free tier needs wider spacing)


def _initialize_gemini():
    """Initialize Google Gemini model for AI text detection."""
    global GEMINI_AVAILABLE, _gemini_model

    try:
        import google.generativeai as genai

        api_key = os.environ.get("GEMINI_API_KEY", "")

        if not api_key or api_key == "your_gemini_api_key_here":
            logger.warning("⚠️ GEMINI_API_KEY not set - using heuristic-only detection")
            logger.warning("   Set your key in backend/.env file")
            GEMINI_AVAILABLE = False
            return

        genai.configure(api_key=api_key)

        _gemini_model = genai.GenerativeModel("gemini-2.5-flash")
        GEMINI_AVAILABLE = True
        logger.info("✅ Google Gemini initialized for AI text detection")

    except ImportError:
        logger.warning("⚠️ google-generativeai not installed")
        logger.warning("   Install with: pip install google-generativeai")
        GEMINI_AVAILABLE = False

    except Exception as e:
        logger.warning(f"⚠️ Gemini initialization failed: {e}")
        GEMINI_AVAILABLE = False


# ================================================
# GEMINI AI DETECTION
# ================================================

AI_DETECTION_PROMPT = """You are an AI-generated text detector for a virtual interview proctoring system.

Analyze the following transcript of spoken words from a candidate during an interview. 
Determine the probability that the candidate is reading answers from an AI assistant 
(like ChatGPT, Gemini, Claude, etc.) versus speaking naturally as a human.

IMPORTANT INDICATORS OF AI-GENERATED SPEECH:
- Overly formal/structured language with perfect grammar
- Use of transitional phrases like "furthermore", "moreover", "in conclusion"
- Lack of filler words (um, uh, like, you know)
- Unnaturally coherent and well-organized responses
- Technical jargon used perfectly without hesitation
- Responses that sound like they were written, not spoken
- Perfect sentence structure without self-correction
- Using phrases typical of AI: "It's important to note", "Let me explain", "In summary"

INDICATORS OF NATURAL HUMAN SPEECH:
- Filler words and pauses (um, uh, like, you know, so)
- Self-corrections and rephrasing
- Informal language and contractions
- Incomplete sentences
- Personal anecdotes and experiences
- Emotional expressions
- Variable sentence length
- Grammar mistakes

TRANSCRIPT TO ANALYZE:
\"\"\"
{transcript}
\"\"\"

Respond in EXACTLY this format (no other text):
AI_SCORE: [number 0-100]
HUMAN_SCORE: [number 0-100]
CONFIDENCE: [number 0-100]
VERDICT: [AI_LIKELY or HUMAN_LIKELY or UNCERTAIN]
REASON_1: [first reason]
REASON_2: [second reason]
REASON_3: [third reason]
"""


def detect_ai_with_gemini(transcript: str) -> Dict:
    """
    Use Google Gemini to detect if transcript is AI-generated.

    Args:
        transcript: Text transcribed from speech

    Returns:
        dict with ai_score, human_score, confidence, verdict, reasons
    """
    global _last_gemini_call

    if not GEMINI_AVAILABLE or _gemini_model is None:
        return None

    # Rate limiting
    now = time.time()
    if now - _last_gemini_call < GEMINI_COOLDOWN:
        return None

    try:
        with _gemini_lock:
            _last_gemini_call = time.time()

            prompt = AI_DETECTION_PROMPT.format(transcript=transcript[:2000])

            # Retry with backoff for free-tier rate limits
            last_error = None
            for attempt in range(3):
                try:
                    response = _gemini_model.generate_content(
                        prompt,
                        generation_config={
                            "temperature": 0.1,
                            "max_output_tokens": 300,
                        }
                    )
                    result_text = response.text.strip()
                    return _parse_gemini_response(result_text)
                except Exception as retry_err:
                    last_error = retry_err
                    wait = (attempt + 1) * 5  # 5s, 10s, 15s
                    logger.warning(f"⚠️ Gemini attempt {attempt+1} failed: {str(retry_err)[:100]}, retrying in {wait}s")
                    time.sleep(wait)

            logger.error(f"❌ Gemini failed after 3 attempts: {last_error}")
            return None

    except Exception as e:
        logger.error(f"❌ Gemini detection error: {e}")
        return None


def _parse_gemini_response(response_text: str) -> Dict:
    """Parse Gemini's structured response."""
    result = {
        "ai_score": 0,
        "human_score": 100,
        "confidence": 50,
        "verdict": "UNCERTAIN",
        "reasons": [],
        "source": "gemini"
    }

    try:
        lines = response_text.strip().split("\n")

        for line in lines:
            line = line.strip()

            if line.startswith("AI_SCORE:"):
                val = line.split(":", 1)[1].strip()
                result["ai_score"] = int(float(val))

            elif line.startswith("HUMAN_SCORE:"):
                val = line.split(":", 1)[1].strip()
                result["human_score"] = int(float(val))

            elif line.startswith("CONFIDENCE:"):
                val = line.split(":", 1)[1].strip()
                result["confidence"] = int(float(val))

            elif line.startswith("VERDICT:"):
                result["verdict"] = line.split(":", 1)[1].strip()

            elif line.startswith("REASON_"):
                reason = line.split(":", 1)[1].strip()
                if reason:
                    result["reasons"].append(reason)

        # Ensure scores are valid
        result["ai_score"] = max(0, min(100, result["ai_score"]))
        result["human_score"] = max(0, min(100, result["human_score"]))
        result["confidence"] = max(0, min(100, result["confidence"]))

    except Exception as e:
        logger.error(f"❌ Gemini response parse error: {e}")
        logger.error(f"   Response was: {response_text[:200]}")

    return result


# ================================================
# HEURISTIC AI DETECTION (FALLBACK / SUPPLEMENT)
# ================================================

# Words and patterns commonly used by AI assistants
AI_SIGNATURE_PHRASES = [
    "first and foremost", "it's important to note", "it's worth mentioning",
    "in conclusion", "to summarize", "as previously mentioned",
    "furthermore", "moreover", "subsequently", "in other words",
    "that being said", "with that in mind", "it goes without saying",
    "let me explain", "to elaborate", "in essence", "fundamentally",
    "comprehensively", "holistically", "synergistically",
    "it is crucial", "it is essential", "it is noteworthy",
    "one could argue", "it can be said", "from a broader perspective"
]

FORMAL_TRANSITION_WORDS = [
    "furthermore", "moreover", "subsequently", "consequently",
    "therefore", "thus", "hence", "accordingly", "nevertheless",
    "nonetheless", "additionally", "specifically", "particularly",
    "essentially", "fundamentally", "ultimately", "predominantly",
    "comprehensively", "significantly", "inherently"
]

HUMAN_FILLER_WORDS = [
    "um", "uh", "like", "you know", "sort of", "kind of",
    "i mean", "well", "so", "actually", "basically",
    "literally", "right", "okay", "alright", "hmm", "ah", "er",
    "i think", "i guess", "i suppose", "maybe", "probably"
]

AI_TECHNICAL_PHRASES = [
    "implementation", "methodology", "comprehensive", "facilitate",
    "optimize", "utilize", "demonstrate", "infrastructure",
    "scalability", "paradigm", "framework", "ecosystem",
    "leveraging", "streamline", "robust", "seamless"
]


def detect_ai_heuristic(text: str) -> Dict:
    """
    Heuristic-based AI text detection.
    Analyzes linguistic patterns to determine if text is AI-generated.

    Args:
        text: Transcript text to analyze

    Returns:
        dict with ai_score, human_score, confidence, verdict, reasons
    """

    if not text or len(text) < 15:
        return {
            "ai_score": 0,
            "human_score": 100,
            "confidence": 10,
            "verdict": "UNCERTAIN",
            "reasons": ["Text too short to analyze"],
            "source": "heuristic"
        }

    text_lower = text.lower()
    words = text_lower.split()
    word_count = len(words)
    ai_score = 0
    reasons = []

    # ===== 1. AI Signature Phrases (strong indicator) =====
    signature_count = sum(1 for phrase in AI_SIGNATURE_PHRASES if phrase in text_lower)
    if signature_count >= 3:
        ai_score += 30
        reasons.append(f"🤖 AI signature phrases detected ({signature_count})")
    elif signature_count >= 1:
        ai_score += 15
        reasons.append(f"🤖 Some AI-typical phrases ({signature_count})")

    # ===== 2. Formal Transition Words =====
    formal_count = sum(1 for word in FORMAL_TRANSITION_WORDS if word in text_lower)
    if formal_count >= 4:
        ai_score += 25
        reasons.append(f"📝 Heavy formal language ({formal_count} transitions)")
    elif formal_count >= 2:
        ai_score += 12
        reasons.append(f"📝 Moderate formal language ({formal_count} transitions)")

    # ===== 3. Lack of Filler Words (strong indicator for speech) =====
    filler_count = sum(1 for filler in HUMAN_FILLER_WORDS if filler in text_lower)
    filler_ratio = filler_count / max(word_count, 1)

    if filler_count == 0 and word_count > 30:
        ai_score += 25
        reasons.append("⚠️ No filler words (unnatural for speech)")
    elif filler_ratio < 0.01 and word_count > 50:
        ai_score += 15
        reasons.append("⚠️ Very few filler words")
    elif filler_ratio > 0.05:
        ai_score -= 15  # Human-like
        reasons.append("✅ Natural filler words present")

    # ===== 4. Sentence Structure Analysis =====
    sentences = [s.strip() for s in text.replace("!", ".").replace("?", ".").split(".") if s.strip()]
    if sentences:
        avg_words_per_sentence = sum(len(s.split()) for s in sentences) / len(sentences)

        # AI tends to write longer, more complex sentences
        if avg_words_per_sentence > 25:
            ai_score += 15
            reasons.append(f"📚 Complex sentences (avg {avg_words_per_sentence:.0f} words)")
        elif avg_words_per_sentence < 8:
            ai_score -= 10  # Short = more human-like for speech
            reasons.append("✅ Short conversational sentences")

        # Check sentence length variance (AI = consistent, Human = variable)
        if len(sentences) >= 3:
            lengths = [len(s.split()) for s in sentences]
            length_std = (sum((l - avg_words_per_sentence) ** 2 for l in lengths) / len(lengths)) ** 0.5
            coefficient_of_variation = length_std / max(avg_words_per_sentence, 1)

            if coefficient_of_variation < 0.3:
                ai_score += 10
                reasons.append("📏 Uniform sentence lengths (AI pattern)")
            elif coefficient_of_variation > 0.7:
                ai_score -= 5
                reasons.append("✅ Variable sentence lengths (natural)")

    # ===== 5. Perfect Grammar (AI indicator) =====
    grammar_errors = text_lower.count("aint") + text_lower.count("gonna") + text_lower.count("wanna")
    contractions = text_lower.count("'") + text_lower.count("n't") + text_lower.count("i'm")

    if grammar_errors == 0 and contractions == 0 and word_count > 40:
        ai_score += 10
        reasons.append("📏 Perfect grammar, no contractions")
    elif contractions > 2:
        ai_score -= 5
        reasons.append("✅ Uses contractions (natural)")

    # ===== 6. Vocabulary Diversity =====
    if word_count > 20:
        unique_ratio = len(set(words)) / word_count
        if unique_ratio > 0.85:
            ai_score += 8
            reasons.append(f"📊 High vocabulary diversity ({unique_ratio:.0%})")

    # ===== 7. Technical Jargon =====
    tech_count = sum(1 for w in AI_TECHNICAL_PHRASES if w in text_lower)
    if tech_count >= 3:
        ai_score += 10
        reasons.append(f"🎓 Heavy technical jargon ({tech_count})")

    # ===== 8. Self-Corrections (human indicator) =====
    correction_markers = ["i mean", "sorry", "wait", "actually no", "let me rephrase",
                          "what i meant", "correction", "no wait"]
    corrections = sum(1 for m in correction_markers if m in text_lower)
    if corrections > 0:
        ai_score -= 15
        reasons.append(f"✅ Self-corrections detected ({corrections})")

    # ===== Clamp and Calculate =====
    ai_score = max(0, min(100, ai_score))
    human_score = 100 - ai_score

    # Confidence based on text length
    if word_count < 20:
        confidence = 20
    elif word_count < 50:
        confidence = 50
    elif word_count < 100:
        confidence = 70
    else:
        confidence = 85

    # Verdict
    if ai_score >= 60:
        verdict = "AI_LIKELY"
    elif ai_score >= 35:
        verdict = "UNCERTAIN"
    else:
        verdict = "HUMAN_LIKELY"

    return {
        "ai_score": ai_score,
        "human_score": human_score,
        "confidence": confidence,
        "verdict": verdict,
        "reasons": reasons[:5],  # Top 5 reasons
        "source": "heuristic"
    }


# ================================================
# COMBINED DETECTION (GEMINI + HEURISTIC)
# ================================================

# Session-level detection history
_session_detection_history: Dict[str, deque] = {}


def detect_ai_text(
    transcript: str,
    session_id: str = "default",
    use_gemini: bool = True
) -> Dict:
    """
    Main AI text detection function.
    Combines Gemini analysis with heuristic analysis for robust detection.

    Args:
        transcript: Text transcribed from candidate speech
        session_id: Session identifier for tracking
        use_gemini: Whether to attempt Gemini API call

    Returns:
        dict with:
          - ai_score (0-100): Likelihood text is AI-generated
          - human_score (0-100): Likelihood text is human
          - confidence (0-100): Detection confidence
          - verdict: AI_LIKELY / HUMAN_LIKELY / UNCERTAIN
          - reasons: List of detection reasons
          - source: "gemini", "heuristic", or "combined"
    """

    if not transcript or len(transcript.strip()) < 10:
        return {
            "ai_score": 0,
            "human_score": 100,
            "confidence": 0,
            "verdict": "UNCERTAIN",
            "reasons": ["Insufficient text"],
            "source": "none"
        }

    # Always run heuristic (fast, no API cost)
    heuristic_result = detect_ai_heuristic(transcript)

    # Try Gemini if available and requested
    gemini_result = None
    if use_gemini and GEMINI_AVAILABLE and len(transcript) >= 30:
        gemini_result = detect_ai_with_gemini(transcript)

    # Combine results
    if gemini_result:
        # Weighted combination: 70% Gemini + 30% Heuristic
        combined_ai_score = int(
            gemini_result["ai_score"] * 0.7 +
            heuristic_result["ai_score"] * 0.3
        )
        combined_human_score = 100 - combined_ai_score
        combined_confidence = int(
            gemini_result["confidence"] * 0.7 +
            heuristic_result["confidence"] * 0.3
        )

        # Merge reasons
        all_reasons = []
        if gemini_result.get("reasons"):
            all_reasons.extend([f"🧠 {r}" for r in gemini_result["reasons"][:3]])
        if heuristic_result.get("reasons"):
            all_reasons.extend(heuristic_result["reasons"][:2])

        # Verdict from combined score
        if combined_ai_score >= 60:
            verdict = "AI_LIKELY"
        elif combined_ai_score >= 35:
            verdict = "UNCERTAIN"
        else:
            verdict = "HUMAN_LIKELY"

        result = {
            "ai_score": combined_ai_score,
            "human_score": combined_human_score,
            "confidence": combined_confidence,
            "verdict": verdict,
            "reasons": all_reasons[:5],
            "source": "combined",
            "gemini_score": gemini_result["ai_score"],
            "heuristic_score": heuristic_result["ai_score"]
        }
    else:
        result = heuristic_result

    # Track history for this session
    if session_id not in _session_detection_history:
        _session_detection_history[session_id] = deque(maxlen=20)

    _session_detection_history[session_id].append({
        "timestamp": time.time(),
        "ai_score": result["ai_score"],
        "verdict": result["verdict"],
        "text_length": len(transcript)
    })

    # Smooth score using history
    history = _session_detection_history[session_id]
    if len(history) >= 3:
        recent_scores = [h["ai_score"] for h in list(history)[-5:]]
        smoothed = int(sum(recent_scores) / len(recent_scores))
        result["smoothed_ai_score"] = smoothed
    else:
        result["smoothed_ai_score"] = result["ai_score"]

    logger.info(
        f"🔍 AI Detection [{result['source']}]: "
        f"AI={result['ai_score']}% Human={result['human_score']}% "
        f"Verdict={result['verdict']} | "
        f"Text: '{transcript[:60]}...'"
    )

    return result


def get_session_ai_summary(session_id: str) -> Dict:
    """Get AI detection summary for a session."""
    history = _session_detection_history.get(session_id, deque())

    if not history:
        return {"session_id": session_id, "total_checks": 0}

    scores = [h["ai_score"] for h in history]
    ai_detections = sum(1 for h in history if h["verdict"] == "AI_LIKELY")

    return {
        "session_id": session_id,
        "total_checks": len(history),
        "ai_detections": ai_detections,
        "avg_ai_score": round(sum(scores) / len(scores), 1),
        "max_ai_score": max(scores),
        "min_ai_score": min(scores),
        "ai_detection_rate": round(ai_detections / len(history) * 100, 1)
    }


def reset_session_detection(session_id: str):
    """Reset detection history for a session."""
    if session_id in _session_detection_history:
        _session_detection_history[session_id].clear()


# ================================================
# INITIALIZATION
# ================================================

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
except ImportError:
    pass

_initialize_gemini()
