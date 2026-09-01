import pytest
from app.services.nlp_service import (
    calculate_text_similarity,
    calculate_semantic_embedding_similarity,
    extract_hazard_urgency,
)


def test_semantic_similarity_paraphrased_descriptions():
    """
    Core Phase 9 benchmark:
    'Large pothole near college gate.' and 'Deep pothole outside university entrance.'
    should be recognized as semantically similar (score >= 0.70).
    """
    text1 = "Large pothole near college gate."
    text2 = "Deep pothole outside university entrance."

    sim = calculate_text_similarity(text1, text2)
    assert sim >= 0.70, f"Expected semantic similarity >= 0.70, got {sim}"


def test_semantic_similarity_synonyms():
    """Tests semantic clustering of municipal infrastructure synonyms."""
    s1 = "Severe flooding blocking highway overpass"
    s2 = "Deep waterlogged road creating barrier on flyover"

    sim = calculate_text_similarity(s1, s2)
    assert sim >= 0.65, f"Expected similarity >= 0.65 for synonym-rich descriptions, got {sim}"


def test_semantic_similarity_dissimilar_texts():
    """Completely different hazards should produce low similarity score (< 0.35)."""
    text1 = "Deep pothole near college gate."
    text2 = "Broken streetlight on residential side alley."

    sim = calculate_text_similarity(text1, text2)
    assert sim < 0.40, f"Expected low similarity, got {sim}"


def test_hazard_urgency_extractor():
    """Critical hazard phrases should be detected with an elevated multiplier."""
    urgent_text = "Severe accident risk with dangerous collapsed sinkhole near school"
    res = extract_hazard_urgency(urgent_text)

    assert res["has_critical_language"] is True
    assert res["urgency_multiplier"] > 1.2
    assert "sinkhole" in res["flagged_keywords"]
    assert "school" in res["flagged_keywords"]
