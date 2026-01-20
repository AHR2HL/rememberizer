"""Load and validate fact domains from JSON files."""

import json
import os
from models import db, Domain, Fact


def load_domain(filepath):
    """
    Load and validate a fact domain from a JSON file.

    Args:
        filepath: Path to the JSON file

    Returns:
        dict: Domain data with keys: domain_name, fields, facts

    Raises:
        ValueError: If JSON is invalid or missing required keys
        FileNotFoundError: If file doesn't exist
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {filepath}: {e}")

    # Validate required keys
    required_keys = ["domain_name", "fields", "facts"]
    missing_keys = [key for key in required_keys if key not in data]
    if missing_keys:
        raise ValueError(f"Missing required keys in {filepath}: {missing_keys}")

    # Validate fields is a list
    if not isinstance(data["fields"], list) or len(data["fields"]) == 0:
        raise ValueError(f"'fields' must be a non-empty list in {filepath}")

    # Validate facts is a list
    if not isinstance(data["facts"], list):
        raise ValueError(f"'facts' must be a list in {filepath}")

    # Validate each fact has all required fields
    for i, fact in enumerate(data["facts"]):
        if not isinstance(fact, dict):
            raise ValueError(f"Fact {i} in {filepath} must be a dict")
        missing_fact_fields = [field for field in data["fields"] if field not in fact]
        if missing_fact_fields:
            raise ValueError(
                f"Fact {i} in {filepath} is missing fields: {missing_fact_fields}"
            )

    return data


def populate_database(domain_dict, filename):
    """
    Insert a domain and its facts into the database.

    Args:
        domain_dict: Domain data dict from load_domain()
        filename: Original filename (for reference)

    Returns:
        Domain: The created Domain object

    Raises:
        ValueError: If domain name already exists
    """
    domain_name = domain_dict["domain_name"]

    # Check if domain already exists
    existing = Domain.query.filter_by(name=domain_name).first()
    if existing:
        raise ValueError(f"Domain '{domain_name}' already exists in database")

    # Create domain
    # JSON domains are system domains, globally available to all users
    domain = Domain(
        name=domain_name,
        filename=filename,
        is_published=True,  # Make globally visible
        created_by=None,  # System domain, no creator
        organization_id=None,  # Global domain, not org-scoped
    )
    domain.set_field_names(domain_dict["fields"])
    db.session.add(domain)
    db.session.flush()  # Get domain.id before adding facts

    # Create facts
    for fact_data in domain_dict["facts"]:
        fact = Fact(domain_id=domain.id)
        fact.set_fact_data(fact_data)
        db.session.add(fact)

    db.session.commit()
    return domain


def scan_facts_directory(directory="facts"):
    """
    Scan a directory for JSON fact files.

    Args:
        directory: Path to directory containing JSON files

    Returns:
        list: List of tuples (filename, full_path) for each .json file
    """
    if not os.path.exists(directory):
        return []

    if not os.path.isdir(directory):
        return []

    json_files = []
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            full_path = os.path.join(directory, filename)
            json_files.append((filename, full_path))

    return sorted(json_files)


def load_domain_from_file(filepath):
    """
    Load a domain from file and populate the database.

    Convenience function that combines load_domain and populate_database.

    Args:
        filepath: Path to JSON file

    Returns:
        Domain: The created Domain object
    """
    filename = os.path.basename(filepath)
    domain_dict = load_domain(filepath)
    return populate_database(domain_dict, filename)


def get_available_domains():
    """
    Get list of available domains from the database.

    Returns:
        list: List of Domain objects
    """
    return Domain.query.all()


def load_all_domains_from_directory(directory="facts"):
    """
    Load all JSON files from a directory into the database.

    Skips files that are already loaded (by domain name).

    Args:
        directory: Path to directory containing JSON files

    Returns:
        list: List of newly loaded Domain objects
    """
    json_files = scan_facts_directory(directory)
    loaded_domains = []

    for filename, filepath in json_files:
        try:
            domain_dict = load_domain(filepath)
            # Check if already exists
            if not Domain.query.filter_by(name=domain_dict["domain_name"]).first():
                domain = populate_database(domain_dict, filename)
                loaded_domains.append(domain)
        except (ValueError, FileNotFoundError) as e:
            print(f"Warning: Could not load {filename}: {e}")
            continue

    return loaded_domains
