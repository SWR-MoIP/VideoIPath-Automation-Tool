# --- Security API Exceptions ---


class DomainNotFoundError(Exception):
    """Exception raised when a domain is not found."""

    pass


class MembershipsNotFoundError(Exception):
    """Exception raised when memberships are not found."""

    pass


class DomainAlreadyExistsError(Exception):
    """Exception raised when a domain to be created already exists."""

    pass


class MembershipAlreadyExistsError(Exception):
    """Exception raised when a membership to be created already exists."""

    pass


class MultipleDomainsFoundError(Exception):
    """Exception raised when multiple domains are found for a given query."""

    pass


class MultipleMembershipsFoundError(Exception):
    """Exception raised when multiple memberships are found for a given query."""

    pass


class DomainAddError(Exception):
    """Exception raised when a domain could not be added."""

    pass


class MembershipAddError(Exception):
    """Exception raised when a membership could not be added."""

    pass


class DomainUpdateError(Exception):
    """Exception raised when a domain could not be updated."""

    pass


class MembershipUpdateError(Exception):
    """Exception raised when a membership could not be updated."""

    pass


class DomainRemoveError(Exception):
    """Exception raised when a domain could not be removed."""

    pass


class MembershipRemoveError(Exception):
    """Exception raised when a membership could not be removed."""

    pass
