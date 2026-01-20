"""Domain-related business logic for domain management and assignments."""

import json
from models import db, Domain, Fact, UserDomainAssignment, User


def get_user_domains(user_id):
    """
    Get all domains assigned to a user.

    Args:
        user_id: ID of the user

    Returns:
        list: List of Domain objects assigned to the user
    """
    assignments = UserDomainAssignment.query.filter_by(user_id=user_id).all()
    domains = [assignment.domain for assignment in assignments]
    return domains


def assign_domain_to_user(user_id, domain_id, assigned_by_id):
    """
    Assign a domain to a user.

    Args:
        user_id: ID of the user (student)
        domain_id: ID of the domain
        assigned_by_id: ID of the user assigning (teacher/admin)

    Returns:
        UserDomainAssignment: The created assignment object

    Raises:
        ValueError: If assignment already exists or domain/user not found
    """
    # Check if user exists
    user = User.query.get(user_id)
    if not user:
        raise ValueError(f"User with ID {user_id} not found")

    # Check if domain exists
    domain = Domain.query.get(domain_id)
    if not domain:
        raise ValueError(f"Domain with ID {domain_id} not found")

    # Check if assignment already exists
    existing = UserDomainAssignment.query.filter_by(
        user_id=user_id, domain_id=domain_id
    ).first()

    if existing:
        raise ValueError("Domain already assigned to user")

    # Create assignment
    assignment = UserDomainAssignment(
        user_id=user_id, domain_id=domain_id, assigned_by=assigned_by_id
    )

    db.session.add(assignment)
    db.session.commit()

    return assignment


def unassign_domain_from_user(user_id, domain_id):
    """
    Unassign a domain from a user.

    Args:
        user_id: ID of the user
        domain_id: ID of the domain

    Returns:
        bool: True if unassigned, False if assignment didn't exist
    """
    assignment = UserDomainAssignment.query.filter_by(
        user_id=user_id, domain_id=domain_id
    ).first()

    if not assignment:
        return False

    db.session.delete(assignment)
    db.session.commit()

    return True


def is_domain_assigned(user_id, domain_id):
    """
    Check if a domain is assigned to a user.

    Args:
        user_id: ID of the user
        domain_id: ID of the domain

    Returns:
        bool: True if domain is assigned to user, False otherwise
    """
    assignment = UserDomainAssignment.query.filter_by(
        user_id=user_id, domain_id=domain_id
    ).first()

    return assignment is not None


def create_custom_domain(name, field_names, facts_data, created_by, organization_id):
    """
    Create a custom domain with facts.

    Args:
        name: Domain name (must be unique)
        field_names: List of field names
        facts_data: List of dicts, each containing fact data
        created_by: User ID of creator
        organization_id: Organization ID

    Returns:
        Domain object

    Raises:
        ValueError: If validation fails
    """
    # Check for duplicate domain name
    existing = Domain.query.filter_by(name=name).first()
    if existing:
        raise ValueError(f"Domain name '{name}' already exists")

    # Validate field names
    if not field_names or len(field_names) < 2:
        raise ValueError("Domain must have at least 2 fields")

    # Validate facts
    if not facts_data or len(facts_data) < 4:
        raise ValueError("Domain must have at least 4 facts (for multiple choice)")

    for fact in facts_data:
        if not all(field in fact for field in field_names):
            raise ValueError("Each fact must have all fields")

    # Create domain
    domain = Domain(
        name=name,
        filename=None,  # User-created, no file
        field_names=json.dumps(field_names),
        created_by=created_by,
        organization_id=organization_id,
        is_published=False,  # Private by default
    )
    db.session.add(domain)
    db.session.flush()  # Get domain.id

    # Create facts
    for fact_data in facts_data:
        fact = Fact(domain_id=domain.id, fact_data=json.dumps(fact_data))
        db.session.add(fact)

    db.session.commit()
    return domain


def update_domain_published_status(domain_id, is_published):
    """
    Publish or unpublish a domain.

    Args:
        domain_id: ID of the domain
        is_published: Boolean for published status

    Returns:
        Domain object

    Raises:
        ValueError: If domain not found
    """
    domain = Domain.query.get(domain_id)
    if not domain:
        raise ValueError("Domain not found")

    domain.is_published = is_published
    db.session.commit()
    return domain


def get_visible_domains(user_id, organization_id):
    """
    Get all domains visible to a teacher/admin.

    Published domains are visible to everyone.
    Unpublished domains are only visible to teachers in the same org.

    Args:
        user_id: ID of the user (not used but kept for consistency)
        organization_id: ID of the user's organization

    Returns:
        List of Domain objects
    """
    # Published domains (visible to everyone)
    published = Domain.query.filter_by(is_published=True).all()

    # Organization-scoped domains (same org as teacher)
    org_domains = Domain.query.filter_by(
        organization_id=organization_id, is_published=False
    ).all()

    # Combine and remove duplicates
    all_domains = list(set(published + org_domains))
    return sorted(all_domains, key=lambda d: d.name)


def is_domain_visible_to_teacher(domain, user):
    """
    Check if teacher can see this domain.

    Args:
        domain: Domain object
        user: User object

    Returns:
        Boolean
    """
    # Published domains visible to all
    if domain.is_published:
        return True
    # Org-scoped visible to same org
    if domain.organization_id == user.organization_id:
        return True
    return False
