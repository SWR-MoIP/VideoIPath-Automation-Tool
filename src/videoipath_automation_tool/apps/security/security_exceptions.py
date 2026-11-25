# --- Security API Exceptions ---


class DomainNotFoundError(Exception):
    """Exception raised when a domain is not found."""


class MembershipsNotFoundError(Exception):
    """Exception raised when memberships are not found."""


class DomainAlreadyExistsError(Exception):
    """Exception raised when a domain to be created already exists."""


class MembershipAlreadyExistsError(Exception):
    """Exception raised when a membership to be created already exists."""


class MultipleDomainsFoundError(Exception):
    """Exception raised when multiple domains are found for a given query."""


class MultipleMembershipsFoundError(Exception):
    """Exception raised when multiple memberships are found for a given query."""


class DomainAddError(Exception):
    """Exception raised when a domain could not be added."""


class MembershipAddError(Exception):
    """Exception raised when a membership could not be added."""


class DomainUpdateError(Exception):
    """Exception raised when a domain could not be updated."""


class MembershipUpdateError(Exception):
    """Exception raised when a membership could not be updated."""


class DomainRemoveError(Exception):
    """Exception raised when a domain could not be removed."""


class MembershipRemoveError(Exception):
    """Exception raised when a membership could not be removed."""
