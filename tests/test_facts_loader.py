"""Tests for fact loading and validation."""

import json
import pytest
from facts_loader import (
    load_domain,
    populate_database,
    scan_facts_directory,
    load_domain_from_file,
    get_available_domains,
    load_all_domains_from_directory,
)
from models import Domain, Fact


def test_load_domain_valid_json(temp_facts_dir, sample_facts):
    """Test loading a valid JSON domain file."""
    json_file = temp_facts_dir / "test.json"
    with open(json_file, "w") as f:
        json.dump(sample_facts, f)

    result = load_domain(str(json_file))
    assert result["domain_name"] == sample_facts["domain_name"]
    assert result["fields"] == sample_facts["fields"]
    assert len(result["facts"]) == len(sample_facts["facts"])


def test_load_domain_file_not_found():
    """Test loading a non-existent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_domain("nonexistent.json")


def test_load_domain_invalid_json(temp_facts_dir):
    """Test loading invalid JSON raises ValueError."""
    json_file = temp_facts_dir / "invalid.json"
    with open(json_file, "w") as f:
        f.write("{ invalid json }")

    with pytest.raises(ValueError, match="Invalid JSON"):
        load_domain(str(json_file))


def test_load_domain_missing_keys(temp_facts_dir):
    """Test loading JSON with missing keys raises ValueError."""
    json_file = temp_facts_dir / "missing_keys.json"
    with open(json_file, "w") as f:
        json.dump({"domain_name": "Test"}, f)

    with pytest.raises(ValueError, match="Missing required keys"):
        load_domain(str(json_file))


def test_load_domain_empty_fields(temp_facts_dir):
    """Test loading JSON with empty fields list raises ValueError."""
    json_file = temp_facts_dir / "empty_fields.json"
    with open(json_file, "w") as f:
        json.dump({"domain_name": "Test", "fields": [], "facts": []}, f)

    with pytest.raises(ValueError, match="non-empty list"):
        load_domain(str(json_file))


def test_load_domain_facts_not_list(temp_facts_dir):
    """Test loading JSON with facts not a list raises ValueError."""
    json_file = temp_facts_dir / "facts_not_list.json"
    with open(json_file, "w") as f:
        json.dump({"domain_name": "Test", "fields": ["field1"], "facts": {}}, f)

    with pytest.raises(ValueError, match="facts.*must be a list"):
        load_domain(str(json_file))


def test_load_domain_fact_missing_field(temp_facts_dir):
    """Test loading JSON with fact missing required field raises ValueError."""
    json_file = temp_facts_dir / "fact_missing_field.json"
    data = {
        "domain_name": "Test",
        "fields": ["field1", "field2"],
        "facts": [{"field1": "value1"}],
    }
    with open(json_file, "w") as f:
        json.dump(data, f)

    with pytest.raises(ValueError, match="missing fields"):
        load_domain(str(json_file))


def test_populate_database(app, sample_facts):
    """Test populating database with domain and facts."""
    with app.app_context():
        domain = populate_database(sample_facts, "test.json")

        assert domain.id is not None
        assert domain.name == sample_facts["domain_name"]
        assert domain.filename == "test.json"

        facts = Fact.query.filter_by(domain_id=domain.id).all()
        assert len(facts) == len(sample_facts["facts"])


def test_populate_database_duplicate_domain(app, sample_facts):
    """Test populating database with duplicate domain name raises ValueError."""
    with app.app_context():
        populate_database(sample_facts, "test.json")

        with pytest.raises(ValueError, match="already exists"):
            populate_database(sample_facts, "test2.json")


def test_scan_facts_directory(temp_facts_dir, sample_facts):
    """Test scanning directory for JSON files."""
    # Create some JSON files
    for i in range(3):
        json_file = temp_facts_dir / f"domain{i}.json"
        with open(json_file, "w") as f:
            json.dump(sample_facts, f)

    # Create a non-JSON file
    other_file = temp_facts_dir / "readme.txt"
    with open(other_file, "w") as f:
        f.write("test")

    results = scan_facts_directory(str(temp_facts_dir))
    assert len(results) == 3
    assert all(filename.endswith(".json") for filename, _ in results)


def test_scan_facts_directory_nonexistent():
    """Test scanning non-existent directory returns empty list."""
    results = scan_facts_directory("nonexistent_directory")
    assert results == []


def test_scan_facts_directory_not_a_directory(tmp_path):
    """Test scanning a file (not directory) returns empty list."""
    file_path = tmp_path / "file.txt"
    with open(file_path, "w") as f:
        f.write("test")

    results = scan_facts_directory(str(file_path))
    assert results == []


def test_load_domain_from_file(app, temp_facts_dir, sample_facts):
    """Test loading domain from file and populating database."""
    json_file = temp_facts_dir / "test.json"
    with open(json_file, "w") as f:
        json.dump(sample_facts, f)

    with app.app_context():
        domain = load_domain_from_file(str(json_file))

        assert domain.id is not None
        assert domain.name == sample_facts["domain_name"]

        facts = Fact.query.filter_by(domain_id=domain.id).all()
        assert len(facts) == len(sample_facts["facts"])


def test_get_available_domains(app, populated_db):
    """Test getting available domains from database."""
    with app.app_context():
        domains = get_available_domains()
        assert len(domains) >= 1
        assert any(d.id == populated_db.id for d in domains)


def test_load_all_domains_from_directory(app, temp_facts_dir, sample_facts):
    """Test loading all domains from a directory."""
    # Create multiple domain files
    for i in range(3):
        domain_data = sample_facts.copy()
        domain_data["domain_name"] = f"Domain {i}"
        json_file = temp_facts_dir / f"domain{i}.json"
        with open(json_file, "w") as f:
            json.dump(domain_data, f)

    with app.app_context():
        loaded = load_all_domains_from_directory(str(temp_facts_dir))
        assert len(loaded) == 3

        # Verify all domains are in database
        all_domains = Domain.query.all()
        assert len(all_domains) == 3


def test_load_all_domains_skips_duplicates(app, temp_facts_dir, sample_facts):
    """Test loading all domains skips already loaded domains."""
    json_file = temp_facts_dir / "test.json"
    with open(json_file, "w") as f:
        json.dump(sample_facts, f)

    with app.app_context():
        # Load once
        loaded1 = load_all_domains_from_directory(str(temp_facts_dir))
        assert len(loaded1) == 1

        # Load again - should skip
        loaded2 = load_all_domains_from_directory(str(temp_facts_dir))
        assert len(loaded2) == 0

        # Should still only have 1 domain
        all_domains = Domain.query.all()
        assert len(all_domains) == 1
