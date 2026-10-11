"""Safe domain errors mapped by the HTTP layer."""
class NotFoundError(Exception):
    pass


class ValidationDomainError(Exception):
    pass


class ConflictError(Exception):
    pass
