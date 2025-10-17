class DBException(Exception):
    """Exception raised for database errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class RecordExistsException(Exception):
    """Exception raised when a record already exists in the database."""

    def __init__(self, message: str):
        super().__init__(message)


class RecordNotFoundException(Exception):
    """Exception raised when a record is not found in the database."""

    def __init__(self, message: str):
        super().__init__(message)
