"""Edge case classifier for analyzing claim characteristics.

This module provides classification of claims into edge case categories based on
their characteristics such as length, complexity, special characters, and language.
"""

import re
import unicodedata
from typing import Dict, List, Set


class EdgeCaseClassifier:
    """Classifier for identifying edge case characteristics in claims."""

    # Classification thresholds
    LONG_CLAIM_THRESHOLD_WORDS = 50  # Claims with >50 words are long
    SHORT_CLAIM_THRESHOLD_WORDS = 5  # Claims with <=5 words are short
    COMPLEX_TECHNICAL_KEYWORDS = {
        "quantum",
        "entanglement",
        "mitochondria",
        "neuroplasticity",
        "crispr",
        "gene editing",
        "photosynthesis",
        "thermodynamics",
        "relativity",
        "algorithm",
        "cryptocurrency",
        "blockchain",
        "neural network",
        "machine learning",
        "dna",
        "rna",
        "protein",
        "enzyme",
        "neurotransmitter",
        "synapse",
        "higgs boson",
        "dark matter",
        "antimatter",
    }

    # Ambiguous phrasing indicators
    AMBIGUOUS_INDICATORS = {
        "some studies",
        "research suggests",
        "may be",
        "may",
        "could be",
        "possibly",
        "perhaps",
        "debated",
        "controversial",
        "opinions vary",
        "uncertain",
        "unclear",
        "mixed evidence",
    }

    # Special character patterns
    SPECIAL_CHAR_PATTERNS = [
        r"[α-ωΑ-Ω]",  # Greek letters
        r"[∀-⋿]",  # Mathematical operators
        r"[₀-₉]",  # Subscripts
        r"[⁰-⁹]",  # Superscripts
        r"[∫∑∏√∞≈≠≤≥±∓∂∇]",  # Common math symbols
    ]

    def __init__(self):
        """Initialize the edge case classifier."""
        self._compiled_patterns = [re.compile(pattern) for pattern in self.SPECIAL_CHAR_PATTERNS]

    def classify_claim(self, claim: str) -> List[str]:
        """Classify claim into edge case categories.

        Args:
            claim: The claim text to classify

        Returns:
            List of edge case category names that apply to this claim
        """
        categories = []

        if self.is_long_claim(claim):
            categories.append("long_claims")

        if self.is_short_claim(claim):
            categories.append("short_claims")

        if self.has_special_characters(claim):
            categories.append("special_characters")

        if self.is_multilingual(claim):
            categories.append("multilingual")

        if self.has_ambiguous_phrasing(claim):
            categories.append("ambiguous_phrasing")

        if self.is_complex_technical(claim):
            categories.append("complex_technical")

        return categories

    def is_long_claim(self, claim: str) -> bool:
        """Check if claim is longer than threshold.

        Args:
            claim: The claim text

        Returns:
            True if claim has more than LONG_CLAIM_THRESHOLD_WORDS words
        """
        word_count = self.count_words(claim)
        return word_count > self.LONG_CLAIM_THRESHOLD_WORDS

    def is_short_claim(self, claim: str) -> bool:
        """Check if claim is shorter than threshold.

        Args:
            claim: The claim text

        Returns:
            True if claim has SHORT_CLAIM_THRESHOLD_WORDS or fewer words
        """
        word_count = self.count_words(claim)
        return word_count <= self.SHORT_CLAIM_THRESHOLD_WORDS

    def has_special_characters(self, claim: str) -> bool:
        """Check for special mathematical or scientific characters.

        Args:
            claim: The claim text

        Returns:
            True if claim contains special characters (Greek, math symbols, etc.)
        """
        for pattern in self._compiled_patterns:
            if pattern.search(claim):
                return True
        return False

    def is_multilingual(self, claim: str) -> bool:
        """Check if claim contains non-Latin scripts.

        Args:
            claim: The claim text

        Returns:
            True if claim contains characters from non-Latin scripts
        """
        # Check for Chinese, Japanese, Korean, Arabic, Cyrillic, etc.
        for char in claim:
            script = self._get_script(char)
            if script in {
                "HAN",  # Chinese/Japanese/Korean characters
                "HIRAGANA",  # Japanese
                "KATAKANA",  # Japanese
                "HANGUL",  # Korean
                "ARABIC",  # Arabic
                "CYRILLIC",  # Russian, etc.
                "HEBREW",  # Hebrew
                "DEVANAGARI",  # Hindi, Sanskrit
                "THAI",  # Thai
            }:
                return True

        return False

    def has_ambiguous_phrasing(self, claim: str) -> bool:
        """Check for ambiguous or uncertain phrasing.

        Args:
            claim: The claim text

        Returns:
            True if claim contains ambiguous language indicators
        """
        claim_lower = claim.lower()
        for indicator in self.AMBIGUOUS_INDICATORS:
            if indicator in claim_lower:
                return True
        return False

    def is_complex_technical(self, claim: str) -> bool:
        """Check if claim contains complex technical terminology.

        Args:
            claim: The claim text

        Returns:
            True if claim contains technical keywords or complex patterns
        """
        claim_lower = claim.lower()

        # Check for technical keywords
        for keyword in self.COMPLEX_TECHNICAL_KEYWORDS:
            if keyword in claim_lower:
                return True

        # Check for scientific notation
        if re.search(r"\d+\.?\d*[eE][+-]?\d+", claim):
            return True

        # Check for chemical formulas (e.g., H2O, CO2, C6H12O6)
        if re.search(r"[A-Z][a-z]?\d+", claim):
            return True

        # Check for Latin scientific names (genus species)
        if re.search(r"\b[A-Z][a-z]+ [a-z]+\b", claim):
            words = claim.split()
            # Look for italicized or capitalized Latin-like names
            for i in range(len(words) - 1):
                if words[i][0].isupper() and words[i + 1].islower():
                    return True

        return False

    def count_words(self, claim: str) -> int:
        """Count words in claim.

        Args:
            claim: The claim text

        Returns:
            Number of words in the claim
        """
        # Split on whitespace and filter out empty strings
        words = [word for word in claim.split() if word.strip()]
        return len(words)

    def analyze_claim(self, claim: str) -> Dict[str, any]:
        """Perform comprehensive analysis of claim characteristics.

        Args:
            claim: The claim text

        Returns:
            Dictionary with detailed analysis results
        """
        categories = self.classify_claim(claim)
        word_count = self.count_words(claim)
        char_count = len(claim)

        return {
            "text": claim,
            "edge_case_categories": categories,
            "word_count": word_count,
            "char_count": char_count,
            "is_long": self.is_long_claim(claim),
            "is_short": self.is_short_claim(claim),
            "has_special_chars": self.has_special_characters(claim),
            "is_multilingual": self.is_multilingual(claim),
            "has_ambiguous_phrasing": self.has_ambiguous_phrasing(claim),
            "is_complex_technical": self.is_complex_technical(claim),
            "avg_word_length": char_count / word_count if word_count > 0 else 0,
            "detected_scripts": self._detect_scripts(claim),
        }

    def batch_classify(self, claims: List[str]) -> List[Dict[str, any]]:
        """Classify multiple claims in batch.

        Args:
            claims: List of claim texts

        Returns:
            List of analysis results for each claim
        """
        return [self.analyze_claim(claim) for claim in claims]

    def get_category_statistics(self, claims: List[str]) -> Dict[str, Dict[str, any]]:
        """Get statistics about edge case categories in a set of claims.

        Args:
            claims: List of claim texts

        Returns:
            Dictionary with statistics for each category
        """
        analyses = self.batch_classify(claims)
        total = len(claims)

        # Count occurrences of each category
        category_counts: Dict[str, int] = {}
        for analysis in analyses:
            for category in analysis["edge_case_categories"]:
                category_counts[category] = category_counts.get(category, 0) + 1

        # Calculate statistics
        stats = {}
        for category, count in category_counts.items():
            stats[category] = {
                "count": count,
                "percentage": (count / total * 100) if total > 0 else 0,
            }

        # Add overall statistics
        stats["_summary"] = {
            "total_claims": total,
            "avg_categories_per_claim": sum(len(a["edge_case_categories"]) for a in analyses)
            / total
            if total > 0
            else 0,
            "avg_word_count": sum(a["word_count"] for a in analyses) / total if total > 0 else 0,
        }

        return stats

    @staticmethod
    def _get_script(char: str) -> str:
        """Get the Unicode script for a character.

        Args:
            char: Single character

        Returns:
            Unicode script name
        """
        try:
            # Get Unicode category name
            name = unicodedata.name(char, "")

            # Extract script from name
            if "CJK" in name or "IDEOGRAPH" in name:
                return "HAN"
            elif "HIRAGANA" in name:
                return "HIRAGANA"
            elif "KATAKANA" in name:
                return "KATAKANA"
            elif "HANGUL" in name:
                return "HANGUL"
            elif "ARABIC" in name:
                return "ARABIC"
            elif "CYRILLIC" in name:
                return "CYRILLIC"
            elif "HEBREW" in name:
                return "HEBREW"
            elif "DEVANAGARI" in name:
                return "DEVANAGARI"
            elif "THAI" in name:
                return "THAI"
            elif "GREEK" in name:
                return "GREEK"
            else:
                return "LATIN"
        except ValueError:
            return "UNKNOWN"

    def _detect_scripts(self, text: str) -> List[str]:
        """Detect all scripts present in text.

        Args:
            text: Text to analyze

        Returns:
            List of unique scripts found
        """
        scripts: Set[str] = set()
        for char in text:
            if char.strip():  # Ignore whitespace
                script = self._get_script(char)
                scripts.add(script)

        # Filter out common/noise scripts
        scripts.discard("UNKNOWN")

        return sorted(scripts)
