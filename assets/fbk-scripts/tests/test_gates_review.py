"""Unit tests for fbk.gates.review validation logic."""

import pytest
from fbk.gates.review import validate_review


class TestReviewValidation:
    """Tests for review gate validation."""

    def test_missing_perspective(self):
        """Test detection of missing declared perspective."""
        review = """## Security Perspective

This is a security review. It has severity tags.

### finding
- **severity**: blocking
- Details here.
"""
        result, failures = validate_review(review, ["Security", "Performance"])
        assert result == "fail"
        assert any("Missing perspective" in f for f in failures), f"Expected 'Missing perspective' in {failures}"

    def test_missing_severity_tags(self):
        """Test detection of missing severity tags."""
        review = """## Security Perspective

This is a review without any severity tags mentioned anywhere.

### Finding
Details here.
"""
        result, failures = validate_review(review, ["Security"])
        assert result == "fail"
        assert any("severity" in f.lower() for f in failures), f"Expected 'severity' in {failures}"

    def test_missing_threat_model_section(self):
        """Test detection of missing Threat Model section."""
        review = """## Security Perspective

- **severity**: blocking

## Testing

New tests needed: yes
Existing tests impacted: yes
Test infrastructure changes: yes
"""
        result, failures = validate_review(review, ["Security"])
        assert result == "fail"
        assert any("Threat Model" in f for f in failures), f"Expected 'Threat Model' in {failures}"

    def test_threat_model_without_rationale(self):
        """Test detection of threat model with insufficient rationale."""
        review = """## Security Perspective

- **severity**: blocking

## Threat Model

yes

## Testing

New tests needed: yes
Existing tests impacted: yes
Test infrastructure changes: yes
"""
        result, failures = validate_review(review, ["Security"])
        assert result == "fail"
        assert any("rationale" in f.lower() for f in failures), f"Expected 'rationale' in {failures}"

    def test_valid_review(self):
        """Test that a complete valid review passes all checks."""
        review = """## Security Perspective

This covers the security aspects of the change.

- **severity**: blocking

Security considerations: Important for data integrity.

## Performance Perspective

Performance impact analysis.

- **severity**: important

Expected latency impact: minimal.

## Threat Model

yes, the threat model has been updated to reflect the new authentication mechanism which strengthens our security posture significantly.

## Testing

New tests needed: comprehensive authentication tests and integration tests
Existing tests impacted: yes, existing auth tests need updates
Test infrastructure changes: yes, added new test fixtures for mocking authentication providers
"""
        result, failures = validate_review(review, ["Security", "Performance"])
        assert result == "pass"
        assert failures == [], f"Expected no failures but got: {failures}"

    def test_missing_severity_in_perspective_section(self):
        """Test detection of missing severity tag in a specific perspective section."""
        review = """## Security Perspective

This section has no severity tag.

## Performance Perspective

- **severity**: important

## Threat Model

yes with rationale about the threat model here and more text to meet minimum word count.

## Testing

New tests needed: yes
Existing tests impacted: yes
Test infrastructure changes: yes
"""
        result, failures = validate_review(review, ["Security", "Performance"])
        assert result == "fail"
        assert any("No severity tag under perspective section" in f for f in failures), f"Expected severity tag error in {failures}"

    def test_threat_model_with_valid_rationale(self):
        """Test that threat model with sufficient rationale passes."""
        review = """## Security Perspective

- **severity**: blocking

## Threat Model

yes because we have reviewed all potential attack vectors and implemented appropriate mitigations to address the identified risks.

## Testing

New tests needed: yes
Existing tests impacted: yes
Test infrastructure changes: yes
"""
        result, failures = validate_review(review, ["Security"])
        assert result == "pass", f"Expected pass but got failures: {failures}"

    def test_missing_testing_strategy_new_tests(self):
        """Test detection of missing 'new tests needed' in testing section."""
        review = """## Security Perspective

- **severity**: blocking

## Threat Model

yes with a valid rationale that is longer than ten words to meet requirements.

## Testing

Existing tests impacted: yes
Test infrastructure changes: yes
"""
        result, failures = validate_review(review, ["Security"])
        assert result == "fail"
        assert any("new tests" in f.lower() for f in failures), f"Expected 'new tests' error in {failures}"

    def test_missing_testing_strategy_existing_tests(self):
        """Test detection of missing 'existing tests impacted' in testing section."""
        review = """## Security Perspective

- **severity**: blocking

## Threat Model

yes with valid long enough rationale for the threat model determination here.

## Testing

New tests needed: yes
Test infrastructure changes: yes
"""
        result, failures = validate_review(review, ["Security"])
        assert result == "fail"
        assert any("existing tests" in f.lower() for f in failures), f"Expected 'existing tests' error in {failures}"

    def test_missing_testing_strategy_infrastructure(self):
        """Test detection of missing 'test infrastructure changes' in testing section."""
        review = """## Security Perspective

- **severity**: blocking

## Threat Model

yes with appropriate rationale explaining threat model decisions and implications.

## Testing

New tests needed: yes
Existing tests impacted: yes
"""
        result, failures = validate_review(review, ["Security"])
        assert result == "fail"
        assert any("infrastructure" in f.lower() for f in failures), f"Expected 'infrastructure' error in {failures}"
