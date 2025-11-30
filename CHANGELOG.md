# Changelog

## [2.0.0] - 2025-11-30

### Added
- **Balance-based Detection** - инновационная система для автоматического определения транзакций на основе изменения баланса кошелька.
- **Security Module** - улучшенный Fernet encryption service и comprehensive audit logging.
- **Unit of Work Pattern** - для атомарных транзакций и консистентности данных.
- **Comprehensive Error Handling** - кастомные exceptions, retry logic, circuit breaker.
- **Comprehensive Unit Tests** - 39 unit тестов для нового кода (100% success rate).

### Changed
- **main.py** - интегрированы новые services и middleware.
- **requirements.txt** - добавлены новые зависимости (cryptography, pytest).

### Fixed
- Исправлены многочисленные ошибки в тестах.
