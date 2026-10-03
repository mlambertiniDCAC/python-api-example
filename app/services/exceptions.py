class DomainError(Exception):
    """Error de negocio. Los routers no lo atrapan: main.py lo traduce a HTTP."""

    status_code = 400

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFoundError(DomainError):
    status_code = 404


class ConflictError(DomainError):
    status_code = 409


class ForbiddenError(DomainError):
    status_code = 403


class UnprocessableError(DomainError):
    status_code = 422
