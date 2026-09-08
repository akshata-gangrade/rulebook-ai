from app.services.conflict_detector import ConflictDetector
from app.services.coverage_detector import CoverageDetector
from app.services.evidence import Evidence


def make_evidence(
    text: str,
    similarity: float,
) -> Evidence:
    return Evidence(
        chunk_id="test-1",
        text=text,
        section="Test Section",
        page=None,
        source_file="test.md",
        similarity=similarity,
    )


def test_coverage_detects_supported_question():
    detector = CoverageDetector(
        similarity_threshold=0.30,
    )

    evidence = [
        make_evidence(
            "Students must maintain 75% attendance.",
            0.45,
        )
    ]

    result = detector.detect(evidence)

    assert result.covered is True
    assert result.evidence_count == 1
    assert result.confidence > 0.80


def test_coverage_detects_unsupported_question():
    detector = CoverageDetector(
        similarity_threshold=0.30,
    )

    evidence = [
        make_evidence(
            "Students must maintain 75% attendance.",
            0.20,
        )
    ]

    result = detector.detect(evidence)

    assert result.covered is False
    assert result.evidence_count == 0


def test_conflict_parser_accepts_conflict():
    result = ConflictDetector._parse_response(
        """
        {
            "conflict": true,
            "confidence": 0.98,
            "reason": "Two applicable rules establish different thresholds."
        }
        """
    )

    assert result.conflict is True
    assert result.confidence == 0.98
    assert result.reason


def test_conflict_parser_accepts_no_conflict():
    result = ConflictDetector._parse_response(
        """
        {
            "conflict": false,
            "confidence": 0.90,
            "reason": "Only one applicable rule was found."
        }
        """
    )

    assert result.conflict is False
    assert result.confidence == 0.90