import re
import math
from typing import Dict, List, Set, Tuple
from collections import Counter
import numpy as np

# Domain-specific semantic clusters for municipal road infrastructure
ROAD_SEMANTIC_SYNONYMS = {
    # Hazard types
    "pothole": ["crater", "cavity", "depression", "pit", "hole", "dents", "rut"],
    "damage": ["crack", "fissure", "broken", "fractured", "faulty", "ruined", "deteriorated"],
    "garbage": ["trash", "waste", "rubbish", "litter", "debris", "dump", "junk", "refuse"],
    "streetlight": ["light", "lamp", "luminaire", "pole", "lantern", "lighting", "fixture"],
    "obstruction": ["blockage", "barrier", "blocked", "tree", "branch", "boulder", "wreckage", "obstacle"],
    "flooding": ["waterlogged", "submerged", "puddle", "overflow", "water", "inundated", "pooling"],
    "sign": ["signboard", "board", "marker", "signal", "traffic sign", "indicator"],
    # Scale & intensity
    "large": ["deep", "huge", "massive", "big", "severe", "major", "giant", "extensive", "heavy"],
    "small": ["minor", "slight", "shallow", "tiny", "little"],
    "danger": ["hazardous", "risk", "perilous", "unsafe", "critical", "severe", "emergency"],
    # Landmarks & Locational terms
    "college": ["university", "campus", "institute", "school", "academy"],
    "gate": ["entrance", "entry", "exit", "portal", "gateway", "door"],
    "near": ["outside", "adjacent", "opposite", "beside", "close", "along", "by", "around", "front"],
    "junction": ["intersection", "crossroad", "crossing", "roundabout", "signal"],
    "bridge": ["flyover", "overpass", "underpass", "culvert"],
    "hospital": ["clinic", "medical center", "healthcare", "emergency room"]
}

# Invert synonym map for fast canonical concept lookup
CONCEPT_LOOKUP: Dict[str, str] = {}
for canonical, synonyms in ROAD_SEMANTIC_SYNONYMS.items():
    CONCEPT_LOOKUP[canonical] = canonical
    for syn in synonyms:
        CONCEPT_LOOKUP[syn] = canonical


def tokenize_text(text: str) -> List[str]:
    """
    Normalizes and tokenizes text into lowercased alphanumeric words.
    Removes common English stop words while preserving core semantic tokens.
    """
    if not text:
        return []
    
    stop_words = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "with",
        "of", "by", "is", "was", "are", "were", "it", "this", "that", "there", "road",
        "street", "very", "front", "back", "side", "here", "please", "kindly", "have"
    }
    
    words = re.findall(r'\b[a-zA-Z0-9]{2,}\b', text.lower())
    return [w for w in words if w not in stop_words]


def get_semantic_tokens(text: str) -> List[str]:
    """
    Tokenizes text and maps words to their canonical semantic concept clusters.
    """
    tokens = tokenize_text(text)
    semantic_tokens = []
    for t in tokens:
        canonical = CONCEPT_LOOKUP.get(t, t)
        semantic_tokens.append(canonical)
    return semantic_tokens


def generate_sentence_embedding(text: str, dim: int = 64) -> np.ndarray:
    """
    Computes a dense semantic sentence embedding vector using combined
    canonical concept projections and character 3-gram hashing.
    """
    tokens = get_semantic_tokens(text)
    if not tokens:
        return np.zeros(dim, dtype=np.float32)

    vec = np.zeros(dim, dtype=np.float32)
    for token in tokens:
        # Token-level hash projection
        token_hash = hash(token) % dim
        vec[token_hash] += 1.5

        # Subword 3-gram projections for spelling robustness
        padded = f"<{token}>"
        for i in range(len(padded) - 2):
            trigram = padded[i:i+3]
            tri_hash = hash(trigram) % dim
            vec[tri_hash] += 0.5

    # L2 normalize
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec


def calculate_semantic_embedding_similarity(text1: str, text2: str) -> float:
    """
    Computes cosine similarity between sentence embeddings of two descriptions.
    Recognizes semantic paraphrases (e.g., 'Large pothole near college gate'
    vs 'Deep pothole outside university entrance').
    """
    if not text1 or not text2:
        return 0.0

    emb1 = generate_sentence_embedding(text1)
    emb2 = generate_sentence_embedding(text2)

    dot = float(np.dot(emb1, emb2))
    return max(0.0, min(1.0, round(dot, 4)))


def calculate_text_similarity(text1: str, text2: str) -> float:
    """
    Computes hybrid natural-language semantic similarity:
    - 60% Dense Sentence Embedding Cosine Similarity (handles synonyms & semantic phrasing)
    - 25% Canonical Concept Token Overlap
    - 15% Exact Character Token Jaccard Overlap
    """
    if not text1 or not text2:
        return 0.0

    # 1. Dense Sentence Embedding Similarity
    emb_sim = calculate_semantic_embedding_similarity(text1, text2)

    # 2. Canonical Concept Overlap
    c_tokens1 = set(get_semantic_tokens(text1))
    c_tokens2 = set(get_semantic_tokens(text2))
    if c_tokens1 and c_tokens2:
        c_intersect = len(c_tokens1.intersection(c_tokens2))
        c_union = len(c_tokens1.union(c_tokens2))
        concept_sim = c_intersect / c_union if c_union > 0 else 0.0
    else:
        concept_sim = 0.0

    # 3. Exact Token Jaccard Overlap
    raw_tokens1 = set(tokenize_text(text1))
    raw_tokens2 = set(tokenize_text(text2))
    if raw_tokens1 and raw_tokens2:
        r_intersect = len(raw_tokens1.intersection(raw_tokens2))
        r_union = len(raw_tokens1.union(raw_tokens2))
        jaccard_sim = r_intersect / r_union if r_union > 0 else 0.0
    else:
        jaccard_sim = 0.0

    # Hybrid blend
    composite = (0.60 * emb_sim) + (0.25 * concept_sim) + (0.15 * jaccard_sim)
    return round(float(composite), 4)


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
