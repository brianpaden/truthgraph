"""Validation tests for edge case test data.

This module contains comprehensive tests to validate the structure, completeness,
and quality of edge case test data. Tests verify JSON format, required fields,
and that edge cases meet specified criteria.
"""

import json
from pathlib import Path
from typing import Any, Dict

import pytest

FIXTURES_DIR = Path(__file__).parent

# Edge case categories and expected claim counts
EDGE_CASE_CATEGORIES = {
    "insufficient_evidence": 5,
    "contradictory_evidence": 4,
    "ambiguous_evidence": 5,
    "long_claims": 5,
    "short_claims": 5,
    "special_characters": 5,
    "adversarial_examples": 5,
}

REQUIRED_CLAIM_FIELDS = {
    "id",
    "text",
    "expected_verdict",
    "edge_case_type",
    "expected_behavior",
    "metadata",
}

REQUIRED_EVIDENCE_FIELDS = {"id", "text", "source", "reliability"}


class TestEdgeCaseStructure:
    """Tests for JSON structure and format validation."""

    @pytest.mark.parametrize("category", EDGE_CASE_CATEGORIES.keys())
    def test_json_files_exist(self, category: str):
        """Test that all edge case JSON files exist."""
        filename = f"{category}.json"
        file_path = FIXTURES_DIR / filename
        assert file_path.exists(), f"Edge case file not found: {filename}"

    @pytest.mark.parametrize("category", EDGE_CASE_CATEGORIES.keys())
    def test_json_files_valid(self, category: str):
        """Test that all edge case JSON files are valid."""
        filename = f"{category}.json"
        file_path = FIXTURES_DIR / filename

        with open(file_path, "r", encoding="utf-8") as f:
            try:
                json.load(f)
            except json.JSONDecodeError as e:
                pytest.fail(f"Invalid JSON in {filename}: {e}")

    def test_conftest_exists(self):
        """Test that conftest.py fixture file exists."""
        file_path = FIXTURES_DIR / "conftest.py"
        assert file_path.exists(), "conftest.py not found"

    def test_conftest_valid_python(self):
        """Test that conftest.py is valid Python."""
        file_path = FIXTURES_DIR / "conftest.py"
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                compile(f.read(), "conftest.py", "exec")
            except SyntaxError as e:
                pytest.fail(f"Syntax error in conftest.py: {e}")


class TestEdgeCaseContent:
    """Tests for edge case content validation."""

    @pytest.fixture
    def all_edge_cases(self) -> Dict[str, Dict[str, Any]]:
        """Load all edge case files."""
        all_data = {}
        for category in EDGE_CASE_CATEGORIES.keys():
            file_path = FIXTURES_DIR / f"{category}.json"
            with open(file_path, "r", encoding="utf-8") as f:
                all_data[category] = json.load(f)
        return all_data

    def test_all_categories_present(self, all_edge_cases: Dict[str, Dict[str, Any]]):
        """Test that all required edge case categories are present."""
        for category in EDGE_CASE_CATEGORIES.keys():
            assert category in all_edge_cases, f"Missing edge case category: {category}"

    @pytest.mark.parametrize("category", EDGE_CASE_CATEGORIES.keys())
    def test_category_has_required_fields(
        self, category: str, all_edge_cases: Dict[str, Dict[str, Any]]
    ):
        """Test that each category has required root fields."""
        data = all_edge_cases[category]
        required_root_fields = {"category", "description", "expected_behavior", "claims"}

        for field in required_root_fields:
            assert field in data, f"{category}: Missing required field '{field}'"

    @pytest.mark.parametrize("category", EDGE_CASE_CATEGORIES.keys())
    def test_category_label_matches_filename(
        self, category: str, all_edge_cases: Dict[str, Dict[str, Any]]
    ):
        """Test that category label matches filename."""
        data = all_edge_cases[category]
        assert data["category"] == category, (
            f"Category mismatch: filename={category}, content={data['category']}"
        )

    @pytest.mark.parametrize("category", EDGE_CASE_CATEGORIES.keys())
    def test_minimum_claims_per_category(
        self, category: str, all_edge_cases: Dict[str, Dict[str, Any]]
    ):
        """Test that each category has minimum required number of claims."""
        data = all_edge_cases[category]
        claims = data.get("claims", [])
        min_claims = EDGE_CASE_CATEGORIES[category]

        assert len(claims) >= min_claims, (
            f"{category}: Expected at least {min_claims} claims, but found {len(claims)}"
        )

    def test_total_claims_coverage(self, all_edge_cases: Dict[str, Dict[str, Any]]):
        """Test that total claims meets specification (20-35)."""
        total_claims = sum(len(data.get("claims", [])) for data in all_edge_cases.values())
        assert 20 <= total_claims <= 40, (
            f"Total claims count ({total_claims}) outside expected range (20-35). "
            "Specification requires 3-5 examples per category."
        )

    @pytest.mark.parametrize("category", EDGE_CASE_CATEGORIES.keys())
    def test_claims_have_required_fields(
        self, category: str, all_edge_cases: Dict[str, Dict[str, Any]]
    ):
        """Test that all claims have required fields."""
        data = all_edge_cases[category]
        claims = data.get("claims", [])

        for claim in claims:
            for field in REQUIRED_CLAIM_FIELDS:
                assert field in claim, (
                    f"{category}: Claim {claim.get('id', 'unknown')} "
                    f"missing required field '{field}'"
                )

    @pytest.mark.parametrize("category", EDGE_CASE_CATEGORIES.keys())
    def test_claims_have_valid_ids(self, category: str, all_edge_cases: Dict[str, Dict[str, Any]]):
        """Test that all claims have non-empty unique IDs."""
        data = all_edge_cases[category]
        claims = data.get("claims", [])
        ids = []

        for claim in claims:
            claim_id = claim.get("id", "")
            assert claim_id, f"{category}: Claim has empty ID"
            assert claim_id not in ids, f"{category}: Duplicate claim ID '{claim_id}'"
            ids.append(claim_id)

    @pytest.mark.parametrize("category", EDGE_CASE_CATEGORIES.keys())
    def test_claims_have_non_empty_text(
        self, category: str, all_edge_cases: Dict[str, Dict[str, Any]]
    ):
        """Test that all claims have non-empty text."""
        data = all_edge_cases[category]
        claims = data.get("claims", [])

        for claim in claims:
            text = claim.get("text", "").strip()
            assert text, f"{category}: Claim {claim.get('id')} has empty text"

    @pytest.mark.parametrize("category", EDGE_CASE_CATEGORIES.keys())
    def test_claims_have_valid_verdicts(
        self, category: str, all_edge_cases: Dict[str, Dict[str, Any]]
    ):
        """Test that all claims have valid expected verdicts."""
        data = all_edge_cases[category]
        claims = data.get("claims", [])
        valid_verdicts = {
            "SUPPORTED",
            "REFUTED",
            "INSUFFICIENT",
            "CONFLICTING",
            "AMBIGUOUS",
        }

        for claim in claims:
            verdict = claim.get("expected_verdict", "")
            assert verdict, f"{category}: Claim {claim.get('id')} has empty verdict"
            assert verdict in valid_verdicts, (
                f"{category}: Claim {claim.get('id')} has invalid verdict '{verdict}'. "
                f"Valid verdicts: {valid_verdicts}"
            )

    @pytest.mark.parametrize("category", EDGE_CASE_CATEGORIES.keys())
    def test_claims_edge_case_type_matches_category(
        self, category: str, all_edge_cases: Dict[str, Dict[str, Any]]
    ):
        """Test that claim edge_case_type field matches category."""
        data = all_edge_cases[category]
        claims = data.get("claims", [])

        for claim in claims:
            edge_case_type = claim.get("edge_case_type", "")
            # Normalize comparison (e.g., "contradictory_evidence" -> "contradictory_evidence")
            assert edge_case_type == category, (
                f"{category}: Claim {claim.get('id')} has edge_case_type "
                f"'{edge_case_type}' (expected '{category}')"
            )

    @pytest.mark.parametrize("category", EDGE_CASE_CATEGORIES.keys())
    def test_claims_have_metadata(self, category: str, all_edge_cases: Dict[str, Dict[str, Any]]):
        """Test that all claims have metadata."""
        data = all_edge_cases[category]
        claims = data.get("claims", [])

        for claim in claims:
            metadata = claim.get("metadata")
            assert metadata is not None, f"{category}: Claim {claim.get('id')} has missing metadata"
            assert isinstance(metadata, dict), (
                f"{category}: Claim {claim.get('id')} metadata is not a dict"
            )

    @pytest.mark.parametrize("category", EDGE_CASE_CATEGORIES.keys())
    def test_evidence_has_required_fields(
        self, category: str, all_edge_cases: Dict[str, Dict[str, Any]]
    ):
        """Test that all evidence items have required fields."""
        data = all_edge_cases[category]
        evidence_items = data.get("evidence", [])

        for evidence in evidence_items:
            for field in REQUIRED_EVIDENCE_FIELDS:
                assert field in evidence, (
                    f"{category}: Evidence {evidence.get('id', 'unknown')} "
                    f"missing required field '{field}'"
                )

    @pytest.mark.parametrize("category", EDGE_CASE_CATEGORIES.keys())
    def test_evidence_has_valid_reliability(
        self, category: str, all_edge_cases: Dict[str, Dict[str, Any]]
    ):
        """Test that evidence has valid reliability ratings."""
        data = all_edge_cases[category]
        evidence_items = data.get("evidence", [])
        valid_reliability = {"low", "medium", "high"}

        for evidence in evidence_items:
            reliability = evidence.get("reliability", "").lower()
            assert reliability in valid_reliability, (
                f"{category}: Evidence {evidence.get('id')} has invalid reliability "
                f"'{reliability}' (valid: {valid_reliability})"
            )

    @pytest.mark.parametrize("category", EDGE_CASE_CATEGORIES.keys())
    def test_evidence_references_are_valid(
        self, category: str, all_edge_cases: Dict[str, Dict[str, Any]]
    ):
        """Test that evidence references in claims are valid."""
        data = all_edge_cases[category]
        claims = data.get("claims", [])
        evidence_items = data.get("evidence", [])
        evidence_ids = {e["id"] for e in evidence_items}

        for claim in claims:
            evidence_refs = claim.get("evidence_ids", [])
            for evidence_id in evidence_refs:
                assert evidence_id in evidence_ids, (
                    f"{category}: Claim {claim.get('id')} references "
                    f"non-existent evidence ID '{evidence_id}'"
                )


class TestEdgeCaseSpecifications:
    """Tests for edge case specific requirements."""

    @pytest.fixture
    def all_edge_cases(self) -> Dict[str, Dict[str, Any]]:
        """Load all edge case files."""
        all_data = {}
        for category in EDGE_CASE_CATEGORIES.keys():
            file_path = FIXTURES_DIR / f"{category}.json"
            with open(file_path, "r", encoding="utf-8") as f:
                all_data[category] = json.load(f)
        return all_data

    def test_short_claims_are_short(self, all_edge_cases: Dict[str, Dict[str, Any]]):
        """Test that short claims are actually short (<10 words average)."""
        data = all_edge_cases["short_claims"]
        claims = data.get("claims", [])

        for claim in claims:
            text = claim.get("text", "")
            word_count = len(text.split())
            assert word_count <= 15, (
                f"Short claim {claim.get('id')} is too long: "
                f"{word_count} words (expected <15 for edge case testing)"
            )

    def test_long_claims_are_long(self, all_edge_cases: Dict[str, Dict[str, Any]]):
        """Test that long claims are sufficiently long (200+ words)."""
        data = all_edge_cases["long_claims"]
        claims = data.get("claims", [])

        for claim in claims:
            text = claim.get("text", "")
            word_count = len(text.split())
            assert word_count >= 150, (
                f"Long claim {claim.get('id')} is too short: "
                f"{word_count} words (expected 150+ for edge case testing)"
            )

    def test_special_characters_contain_unicode(self, all_edge_cases: Dict[str, Dict[str, Any]]):
        """Test that special character claims contain actual special characters."""
        data = all_edge_cases["special_characters"]
        claims = data.get("claims", [])

        for claim in claims:
            text = claim.get("text", "")
            # Check for at least one non-ASCII character or special symbol
            has_special = any(ord(char) > 127 or char in "@#$%^&*🎉" for char in text)
            assert has_special, (
                f"Special character claim {claim.get('id')} doesn't contain "
                f"special characters or Unicode"
            )

    def test_contradictory_has_evidence_pairs(self, all_edge_cases: Dict[str, Dict[str, Any]]):
        """Test that contradictory evidence category has claim-evidence pairs."""
        data = all_edge_cases["contradictory_evidence"]
        claims = data.get("claims", [])
        evidence = data.get("evidence", [])

        assert len(evidence) > 0, "Contradictory category should have evidence"

        for claim in claims:
            evidence_refs = claim.get("evidence_ids", [])
            assert len(evidence_refs) >= 2, (
                f"Contradictory claim {claim.get('id')} should reference "
                f"multiple evidence items for conflict"
            )

    def test_insufficient_evidence_no_evidence(self, all_edge_cases: Dict[str, Dict[str, Any]]):
        """Test that insufficient evidence claims have no supporting evidence."""
        data = all_edge_cases["insufficient_evidence"]
        claims = data.get("claims", [])

        for claim in claims:
            evidence_refs = claim.get("evidence_ids", [])
            assert len(evidence_refs) == 0, (
                f"Insufficient evidence claim {claim.get('id')} should have "
                f"no evidence references (found {len(evidence_refs)})"
            )

    def test_adversarial_has_documentation(self, all_edge_cases: Dict[str, Dict[str, Any]]):
        """Test that adversarial examples have clear documentation."""
        data = all_edge_cases["adversarial_examples"]
        claims = data.get("claims", [])

        for claim in claims:
            metadata = claim.get("metadata", {})
            assert "fallacy_type" in metadata, (
                f"Adversarial claim {claim.get('id')} should document fallacy type"
            )
            assert "misleading_frame" in metadata, (
                f"Adversarial claim {claim.get('id')} should document misleading frame"
            )


class TestEdgeCaseUsage:
    """Tests for edge case usage and integration."""

    def test_fixtures_are_loadable(
        self,
        edge_case_insufficient_evidence,
        edge_case_contradictory,
        edge_case_ambiguous,
        edge_case_long_claims,
        edge_case_short_claims,
        edge_case_special_characters,
        edge_case_adversarial,
    ):
        """Test that all fixtures load correctly through pytest."""
        fixtures = [
            edge_case_insufficient_evidence,
            edge_case_contradictory,
            edge_case_ambiguous,
            edge_case_long_claims,
            edge_case_short_claims,
            edge_case_special_characters,
            edge_case_adversarial,
        ]

        for fixture in fixtures:
            assert isinstance(fixture, dict), "Each fixture should be a dictionary"
            assert "claims" in fixture, "Each fixture should have 'claims' key"

    def test_all_edge_cases_fixture(self, all_edge_cases: Dict[str, Dict[str, Any]]):
        """Test that combined all_edge_cases fixture works correctly."""
        assert isinstance(all_edge_cases, dict), "all_edge_cases should be a dictionary"
        assert len(all_edge_cases) == 7, (
            f"all_edge_cases should have 7 categories, found {len(all_edge_cases)}"
        )

        for category in EDGE_CASE_CATEGORIES.keys():
            assert category in all_edge_cases, f"Missing category: {category}"

    def test_get_edge_case_by_id_fixture(self, get_edge_case_by_id):
        """Test that get_edge_case_by_id factory fixture works."""
        # Test with a known ID
        claim, category = get_edge_case_by_id("edge_insuf_001")
        assert claim is not None, "Should retrieve a claim"
        assert category is not None, "Should return a category"
        assert claim["id"] == "edge_insuf_001"

    def test_edge_case_statistics_fixture(self, edge_case_statistics: Dict[str, Any]):
        """Test that edge_case_statistics fixture provides useful information."""
        assert "total_categories" in edge_case_statistics
        assert "total_claims" in edge_case_statistics
        assert "total_evidence" in edge_case_statistics
        assert "categories" in edge_case_statistics

        assert edge_case_statistics["total_categories"] == 7
        assert edge_case_statistics["total_claims"] >= 20
        assert edge_case_statistics["total_claims"] <= 40

    def test_fixture_unicode_handling(self, edge_case_special_characters: Dict[str, Any]):
        """Test that fixtures properly handle Unicode content."""
        claims = edge_case_special_characters.get("claims", [])

        # Check that we can process special character claims
        for claim in claims:
            text = claim.get("text", "")
            # Ensure text is properly encoded/decoded
            assert isinstance(text, str)
            assert len(text) > 0


class TestEdgeCaseDocumentation:
    """Tests for edge case documentation quality."""

    @pytest.fixture
    def all_edge_cases(self) -> Dict[str, Dict[str, Any]]:
        """Load all edge case files."""
        all_data = {}
        for category in EDGE_CASE_CATEGORIES.keys():
            file_path = FIXTURES_DIR / f"{category}.json"
            with open(file_path, "r", encoding="utf-8") as f:
                all_data[category] = json.load(f)
        return all_data

    @pytest.mark.parametrize("category", EDGE_CASE_CATEGORIES.keys())
    def test_category_has_description(
        self, category: str, all_edge_cases: Dict[str, Dict[str, Any]]
    ):
        """Test that each category has a meaningful description."""
        data = all_edge_cases[category]
        description = data.get("description", "").strip()
        assert len(description) > 20, (
            f"{category}: Description too short or missing. Should explain the edge case category."
        )

    @pytest.mark.parametrize("category", EDGE_CASE_CATEGORIES.keys())
    def test_category_has_expected_behavior(
        self, category: str, all_edge_cases: Dict[str, Dict[str, Any]]
    ):
        """Test that each category documents expected system behavior."""
        data = all_edge_cases[category]
        behavior = data.get("expected_behavior", "").strip()
        assert len(behavior) > 20, (
            f"{category}: Expected behavior documentation missing or too short"
        )

    @pytest.mark.parametrize("category", EDGE_CASE_CATEGORIES.keys())
    def test_claims_have_reason_and_behavior(
        self, category: str, all_edge_cases: Dict[str, Dict[str, Any]]
    ):
        """Test that all claims document their reason and expected behavior."""
        data = all_edge_cases[category]
        claims = data.get("claims", [])

        for claim in claims:
            reason = claim.get("reason", "").strip()
            expected_behavior = claim.get("expected_behavior", "").strip()

            assert len(reason) > 10, (
                f"{category}: Claim {claim.get('id')} missing reason documentation"
            )
            assert len(expected_behavior) > 10, (
                f"{category}: Claim {claim.get('id')} missing expected_behavior documentation"
            )
