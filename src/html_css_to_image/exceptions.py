"""Exceptions raised by the HTML/CSS to Image client."""


class UnexpectedResponseError(Exception):
    """The API returned a successful response with an unexpected body.

    This indicates that the client could not safely construct its documented
    success model. API-declared errors are returned as ``ApiErrorResponse``;
    HTTP transport failures continue to be raised by HTTPX.

    Args:
        message: Description of the malformed response.
        status_code: HTTP status code returned by the API.

    Attributes:
        status_code: HTTP status code returned by the API.
    """

    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code
