import re
import math
from typing import Dict, List, Set
from collections import Counter


def tokenize_text(text: str) -> List[str]:
    """
    Normalizes and tokenizes text into lowercased alphanumeric words.
    Removes common English stop words.
    """
    if not text:
        return []
    
    stop_words = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "with",
        "of", "by", "is", "was", "are", "were", "it", "this", "that", "there", "road",
        "street", "very", "near", "front", "back", "side", "here"
    }
    
    words = re.findall(r'\b[a-zA-Z0-9]{2,}\b', text.lower())
    return [w for w in words if w not in stop_words]


def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    Computes semantic text similarity score in [0.0, 1.0] using
    a hybrid of Cosine Term-Frequency similarity and Jaccard word token overlap.
    """
    if not text1 or not text2:
        return 0.0
    
    tokens1 = tokenize_text(text1)
    tokens2 = tokenize_text(text2)
    
    if not tokens1 or not tokens2:
        return 0.0

    # 1. Jaccard token overlap
    set1, set2 = set(tokens1), set(tokens2)
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    jaccard = intersection / union if union > 0 else 0.0

    # 2. Term Frequency (Cosine similarity)
    vec1 = Counter(tokens1)
    vec2 = Counter(tokens2)
    
    dot_product = sum(vec1[w] * vec2[w] for w in set1.intersection(set2))
    mag1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
    mag2 = math.sqrt(sum(v ** 2 for v in vec2.values()))
    
    cosine = (dot_product / (mag1 * mag2)) if (mag1 * mag2) > 0 else 0.0

    # Weighted blend (60% Cosine, 40% Jaccard)
    return round(0.6 * cosine + 0.4 * jaccard, 3)


def extract_hazard_urgency(text: str) -> Dict[str, any]:
    """
    Analyzes citizen report descriptions for high-urgency keywords,
    vulnerable zones, and pedestrian hazards.
    """
    if not text:
        return {"urgency_multiplier": 1.0, "flagged_keywords": []}

    critical_keywords = {
        "accident": 1.25,
        "crash": 1.25,
        "collapsed": 1.30,
        "sinkhole": 1.35,
        "danger": 1.15,
        "dangerous": 1.15,
        "emergency": 1.30,
        "ambulance": 1.20,
        "hospital": 1.20,
        "school": 1.15,
        "children": 1.15,
        "injury": 1.25,
        "flood": 1.20,
        "blocked": 1.15,
        "traffic": 1.10
    }

    words = tokenize_text(text)
    matched = []
    max_multiplier = 1.0

    for word in words:
        if word in critical_keywords:
            matched.append(word)
            if critical_keywords[word] > max_multiplier:
                max_multiplier = critical_keywords[word]

    return {
        "urgency_multiplier": max_multiplier,
        "flagged_keywords": list(set(matched)),
        "has_critical_language": len(matched) > 0
    }
