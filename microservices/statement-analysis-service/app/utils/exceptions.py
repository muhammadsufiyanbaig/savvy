class StatementAnalysisError(Exception):
    """Base exception for statement analysis errors."""


class ParsingError(StatementAnalysisError):
    """Error during document parsing (PDF / CSV / Excel)."""


class AIExtractionError(StatementAnalysisError):
    """Error during AI-powered transaction extraction."""


class CategorizationError(StatementAnalysisError):
    """Error during transaction categorization."""


class S3DownloadError(StatementAnalysisError):
    """Error downloading statement from S3."""


class UnsupportedFileTypeError(StatementAnalysisError):
    """File type not supported."""
