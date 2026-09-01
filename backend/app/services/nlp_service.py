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
    "large": ["deep", "huge", "massive", "big", "severe", "major", "giant", "extensive", "heavy", "critical"],
    "small": ["minor", "slight", "shallow", "tiny", "little"],
    "danger": ["hazardous", "risk", "perilous", "unsafe", "emergency"],
    # Landmarks & Locational terms
    "college": ["university", "campus", "institute", "school", "academy"],
    "gate": ["entrance", "entry", "exit", "portal", "gateway", "door"],
    "near": ["outside", "adjacent", "opposite", "beside", "close", "along", "by", "around"],
    "junction": ["intersection", "crossroad", "crossing", "roundabout", "signal"],
    "road": ["highway", "freeway", "expressway", "street", "avenue", "lane", "corridor", "drive", "way"],
    "bridge": ["flyover", "overpass", "underpass", "culvert", "causeway"],
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
    Removes standard functional English stop words while retaining domain nouns/adjectives.
    """
    if not text:
        return []
    
    stop_words = {
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "with",
        "of", "by", "is", "was", "are", "were", "it", "this", "that", "there",
        "very", "here", "please", "kindly", "have", "has", "had", "be", "been"
    }
    
    words = re.findall(r'\b[a-zA-Z0-9]{2,}\b', text.lower())
    return [w for w in words if w not in stop_words]


import hashlib

def stem_token(word: str) -> str:
    """Simple rule-based suffix normalization for road infrastructure terms."""
    w = word.lower()
    for suffix in ["ing", "ed", "es", "ly", "tion", "s"]:
        if len(w) > len(suffix) + 3 and w.endswith(suffix):
            w = w[:-len(suffix)]
            break
    return w


def get_semantic_tokens(text: str) -> List[str]:
    """
    Tokenizes text, stems words, and maps them to canonical semantic concept clusters.
    """
    tokens = tokenize_text(text)
    semantic_tokens = []
    for t in tokens:
        stemmed = stem_token(t)
        canonical = CONCEPT_LOOKUP.get(t, CONCEPT_LOOKUP.get(stemmed, stemmed))
        semantic_tokens.append(canonical)
    return semantic_tokens


def generate_sentence_embedding(text: str, dim: int = 64) -> np.ndarray:
    """
    Computes a deterministic dense semantic sentence embedding vector using combined
    canonical concept projections and character 3-gram hashing.
    """
    tokens = get_semantic_tokens(text)
    if not tokens:
        return np.zeros(dim, dtype=np.float32)

    vec = np.zeros(dim, dtype=np.float32)
    for token in tokens:
        # Deterministic token-level hash projection
        h = int(hashlib.md5(token.encode('utf-8')).hexdigest(), 16)
        token_hash = h % dim
        vec[token_hash] += 2.0

        # Subword 3-gram projections for spelling robustness
        padded = f"<{token}>"
        for i in range(len(padded) - 2):
            trigram = padded[i:i+3]
            tri_h = int(hashlib.md5(trigram.encode('utf-8')).hexdigest(), 16)
            tri_hash = tri_h % dim
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

    # 2. Canonical Concept Vector Cosine Similarity
    c_tokens1 = get_semantic_tokens(text1)
    c_tokens2 = get_semantic_tokens(text2)
    if c_tokens1 and c_tokens2:
        vec1 = Counter(c_tokens1)
        vec2 = Counter(c_tokens2)
        dot = sum(vec1[w] * vec2[w] for w in set(c_tokens1).intersection(set(c_tokens2)))
        mag1 = math.sqrt(sum(v ** 2 for v in vec1.values()))
        mag2 = math.sqrt(sum(v ** 2 for v in vec2.values()))
        concept_cosine = (dot / (mag1 * mag2)) if (mag1 * mag2) > 0 else 0.0
    else:
        concept_cosine = 0.0

    # 3. Exact Token Jaccard Overlap
    raw_tokens1 = set(tokenize_text(text1))
    raw_tokens2 = set(tokenize_text(text2))
    if raw_tokens1 and raw_tokens2:
        r_intersect = len(raw_tokens1.intersection(raw_tokens2))
        r_union = len(raw_tokens1.union(raw_tokens2))
        jaccard_sim = r_intersect / r_union if r_union > 0 else 0.0
    else:
        jaccard_sim = 0.0

    # Hybrid blend: 50% Embedding Cosine, 40% Concept Cosine, 10% Raw Token Overlap
    composite = (0.50 * emb_sim) + (0.40 * concept_cosine) + (0.10 * jaccard_sim)
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
