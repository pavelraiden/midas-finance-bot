"""
Custom Exception Hierarchy для Midas Financial Bot.

Provides clear, structured error handling с user-friendly messages.
"""


class MidasException(Exception):
    """
    Base exception для всех Midas-specific errors.
    
    Attributes:
        message: User-friendly error message
        code: Error code для логирования
        details: Additional error details
    """
    
    def __init__(
        self,
        message: str,
        code: str = "UNKNOWN_ERROR",
        details: dict = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> dict:
        """Converts exception to dict для logging/API responses."""
        return {
            "error_type": self.__class__.__name__,
            "code": self.code,
            "message": self.message,
            "details": self.details
        }


# ============================================================================
# DATABASE ERRORS
# ============================================================================

class DatabaseError(MidasException):
    """Base class для database errors."""
    pass


class RecordNotFoundError(DatabaseError):
    """Raised when database record not found."""
    
    def __init__(self, entity: str, identifier: any):
        super().__init__(
            message=f"{entity} not found: {identifier}",
            code="RECORD_NOT_FOUND",
            details={"entity": entity, "identifier": str(identifier)}
        )


class DuplicateRecordError(DatabaseError):
    """Raised when trying to create duplicate record."""
    
    def __init__(self, entity: str, field: str, value: any):
        super().__init__(
            message=f"{entity} with {field}={value} already exists",
            code="DUPLICATE_RECORD",
            details={"entity": entity, "field": field, "value": str(value)}
        )


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection fails."""
    
    def __init__(self, details: str = ""):
        super().__init__(
            message=f"Database connection failed: {details}",
            code="DB_CONNECTION_ERROR",
            details={"reason": details}
        )


# ============================================================================
# VALIDATION ERRORS
# ============================================================================

class ValidationError(MidasException):
    """Base class для validation errors."""
    pass


class InvalidAmountError(ValidationError):
    """Raised when amount is invalid."""
    
    def __init__(self, amount: any, reason: str = ""):
        super().__init__(
            message=f"Invalid amount: {amount}. {reason}",
            code="INVALID_AMOUNT",
            details={"amount": str(amount), "reason": reason}
        )


class InvalidCurrencyError(ValidationError):
    """Raised when currency is invalid."""
    
    def __init__(self, currency: str):
        super().__init__(
            message=f"Invalid currency: {currency}",
            code="INVALID_CURRENCY",
            details={"currency": currency}
        )


class InvalidDateError(ValidationError):
    """Raised when date is invalid."""
    
    def __init__(self, date: any, reason: str = ""):
        super().__init__(
            message=f"Invalid date: {date}. {reason}",
            code="INVALID_DATE",
            details={"date": str(date), "reason": reason}
        )


class InsufficientBalanceError(ValidationError):
    """Raised when wallet balance is insufficient."""
    
    def __init__(self, wallet_id: int, required: float, available: float):
        super().__init__(
            message=f"Insufficient balance in wallet {wallet_id}: required {required}, available {available}",
            code="INSUFFICIENT_BALANCE",
            details={
                "wallet_id": wallet_id,
                "required": required,
                "available": available
            }
        )


# ============================================================================
# EXTERNAL API ERRORS
# ============================================================================

class ExternalAPIError(MidasException):
    """Base class для external API errors."""
    pass


class BlockchainAPIError(ExternalAPIError):
    """Raised when blockchain API call fails."""
    
    def __init__(self, provider: str, reason: str):
        super().__init__(
            message=f"Blockchain API error ({provider}): {reason}",
            code="BLOCKCHAIN_API_ERROR",
            details={"provider": provider, "reason": reason}
        )


class AIServiceError(ExternalAPIError):
    """Raised when AI service call fails."""
    
    def __init__(self, service: str, reason: str):
        super().__init__(
            message=f"AI service error ({service}): {reason}",
            code="AI_SERVICE_ERROR",
            details={"service": service, "reason": reason}
        )


class RateLimitExceededError(ExternalAPIError):
    """Raised when API rate limit exceeded."""
    
    def __init__(self, service: str, retry_after: int = None):
        message = f"Rate limit exceeded for {service}"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            details={"service": service, "retry_after": retry_after}
        )


# ============================================================================
# BUSINESS LOGIC ERRORS
# ============================================================================

class BusinessLogicError(MidasException):
    """Base class для business logic errors."""
    pass


class WalletNotFoundError(BusinessLogicError):
    """Raised when wallet not found."""
    
    def __init__(self, wallet_id: int):
        super().__init__(
            message=f"Wallet not found: {wallet_id}",
            code="WALLET_NOT_FOUND",
            details={"wallet_id": wallet_id}
        )


class CategoryNotFoundError(BusinessLogicError):
    """Raised when category not found."""
    
    def __init__(self, category_id: int):
        super().__init__(
            message=f"Category not found: {category_id}",
            code="CATEGORY_NOT_FOUND",
            details={"category_id": category_id}
        )


class TransactionNotFoundError(BusinessLogicError):
    """Raised when transaction not found."""
    
    def __init__(self, transaction_id: int):
        super().__init__(
            message=f"Transaction not found: {transaction_id}",
            code="TRANSACTION_NOT_FOUND",
            details={"transaction_id": transaction_id}
        )


class DuplicateTransactionError(BusinessLogicError):
    """Raised when duplicate transaction detected."""
    
    def __init__(self, source_id: str, source_type: str):
        super().__init__(
            message=f"Duplicate transaction detected: {source_type}:{source_id}",
            code="DUPLICATE_TRANSACTION",
            details={"source_id": source_id, "source_type": source_type}
        )


# ============================================================================
# IMPORT/EXPORT ERRORS
# ============================================================================

class ImportError(MidasException):
    """Base class для import errors."""
    pass


class CSVParseError(ImportError):
    """Raised when CSV parsing fails."""
    
    def __init__(self, filename: str, row: int, reason: str):
        super().__init__(
            message=f"CSV parse error in {filename} at row {row}: {reason}",
            code="CSV_PARSE_ERROR",
            details={"filename": filename, "row": row, "reason": reason}
        )


class UnsupportedFormatError(ImportError):
    """Raised when file format is unsupported."""
    
    def __init__(self, filename: str, format: str):
        super().__init__(
            message=f"Unsupported format: {format} in file {filename}",
            code="UNSUPPORTED_FORMAT",
            details={"filename": filename, "format": format}
        )


# ============================================================================
# SECURITY ERRORS
# ============================================================================

class SecurityError(MidasException):
    """Base class для security errors."""
    pass


class UnauthorizedError(SecurityError):
    """Raised when user is not authorized."""
    
    def __init__(self, user_id: int, action: str):
        super().__init__(
            message=f"User {user_id} is not authorized to perform: {action}",
            code="UNAUTHORIZED",
            details={"user_id": user_id, "action": action}
        )


class EncryptionError(SecurityError):
    """Raised when encryption fails."""
    
    def __init__(self, reason: str):
        super().__init__(
            message=f"Encryption failed: {reason}",
            code="ENCRYPTION_ERROR",
            details={"reason": reason}
        )


class DecryptionError(SecurityError):
    """Raised when decryption fails."""
    
    def __init__(self, reason: str):
        super().__init__(
            message=f"Decryption failed: {reason}",
            code="DECRYPTION_ERROR",
            details={"reason": reason}
        )


# ============================================================================
# USER-FRIENDLY ERROR MESSAGES
# ============================================================================

ERROR_MESSAGES = {
    # Russian messages
    "ru": {
        "RECORD_NOT_FOUND": "Запись не найдена",
        "DUPLICATE_RECORD": "Такая запись уже существует",
        "DB_CONNECTION_ERROR": "Ошибка подключения к базе данных",
        "INVALID_AMOUNT": "Неверная сумма",
        "INVALID_CURRENCY": "Неверная валюта",
        "INVALID_DATE": "Неверная дата",
        "INSUFFICIENT_BALANCE": "Недостаточно средств",
        "BLOCKCHAIN_API_ERROR": "Ошибка blockchain API",
        "AI_SERVICE_ERROR": "Ошибка AI сервиса",
        "RATE_LIMIT_EXCEEDED": "Превышен лимит запросов",
        "WALLET_NOT_FOUND": "Кошелек не найден",
        "CATEGORY_NOT_FOUND": "Категория не найдена",
        "TRANSACTION_NOT_FOUND": "Транзакция не найдена",
        "DUPLICATE_TRANSACTION": "Дубликат транзакции",
        "CSV_PARSE_ERROR": "Ошибка парсинга CSV",
        "UNSUPPORTED_FORMAT": "Неподдерживаемый формат",
        "UNAUTHORIZED": "Нет доступа",
        "ENCRYPTION_ERROR": "Ошибка шифрования",
        "DECRYPTION_ERROR": "Ошибка дешифрования",
    },
    # English messages
    "en": {
        "RECORD_NOT_FOUND": "Record not found",
        "DUPLICATE_RECORD": "Record already exists",
        "DB_CONNECTION_ERROR": "Database connection error",
        "INVALID_AMOUNT": "Invalid amount",
        "INVALID_CURRENCY": "Invalid currency",
        "INVALID_DATE": "Invalid date",
        "INSUFFICIENT_BALANCE": "Insufficient balance",
        "BLOCKCHAIN_API_ERROR": "Blockchain API error",
        "AI_SERVICE_ERROR": "AI service error",
        "RATE_LIMIT_EXCEEDED": "Rate limit exceeded",
        "WALLET_NOT_FOUND": "Wallet not found",
        "CATEGORY_NOT_FOUND": "Category not found",
        "TRANSACTION_NOT_FOUND": "Transaction not found",
        "DUPLICATE_TRANSACTION": "Duplicate transaction",
        "CSV_PARSE_ERROR": "CSV parse error",
        "UNSUPPORTED_FORMAT": "Unsupported format",
        "UNAUTHORIZED": "Unauthorized",
        "ENCRYPTION_ERROR": "Encryption error",
        "DECRYPTION_ERROR": "Decryption error",
    }
}


def get_user_friendly_message(exception: Exception, language: str = "en") -> str:
    """
    Получает user-friendly error message.
    
    Args:
        exception: Exception instance (MidasException or standard Exception)
        language: Language code ('en', 'ru')
    
    Returns:
        User-friendly error message
    """
    if isinstance(exception, MidasException):
        messages = ERROR_MESSAGES.get(language, ERROR_MESSAGES["en"])
        return messages.get(exception.code, exception.message)
    else:
        # For standard exceptions, return a generic message
        if language == "ru":
            return f"Произошла ошибка: {str(exception)}"
        else:
            return f"An error occurred: {str(exception)}"
