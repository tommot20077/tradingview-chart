# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [asset-core 0.2.1] - 2025-07-02

### Added
- **Missing Unit Tests**: Added comprehensive unit tests for previously untested components:
  - `tests/asset_core/units/network/test_ws_client.py`: WebSocket client unit tests
  - `tests/asset_core/units/observability/test_logging.py`: Logging system unit tests 
  - `tests/asset_core/units/observability/test_metrics.py`: Metrics system unit tests
- **Test Coverage Analysis**: Added detailed analysis documentation (`missing_tests.md`, `missing_tests_analysis.md`) identifying missing test cases and test categorization suggestions

### Enhanced
- **Core Architecture**: Comprehensive improvements across all asset_core modules (31 files modified)
- **Code Documentation**: Enhanced ABOUTME comments and inline documentation throughout the codebase
- **Test Framework**: Significant updates to existing test suites with improved coverage and reliability
- **Build Configuration**: Updated project dependencies and development tooling configuration

### Improved
- **Code Quality**: Extensive refactoring and code formatting improvements across 91 files
- **Test Organization**: Better categorization of unit vs integration tests
- **Error Handling**: Enhanced exception handling and validation throughout the system
- **Performance**: Optimized data models and observability components

### Infrastructure
- **Project Structure**: Continued refinement of the unified monorepo structure
- **Testing Tools**: Enhanced test engine with improved path handling and validation
- **Development Workflow**: Improved build scripts and dependency management

---

## [asset-core 0.2.0] - 2025-06-29

### Changed
- **Unified Project Structure**: Migrated the entire project to a unified monorepo structure managed by a single root `pyproject.toml` and `setuptools`.
- **Simplified Module Layout**: Flattened the directory structure for `asset_core` and `crypto_single` from a nested (`module/module`) to a single-level (`module`) layout, resulting in cleaner import paths.
- **Centralized Dependencies**: Consolidated all project dependencies into the root `pyproject.toml`, using `project.optional-dependencies` to manage dependencies for different applications and development.
- **Unified Test Directory**: Moved all tests to a root-level `tests/` directory, organized by module, for centralized test management and execution.

### Removed
- **Module-specific `pyproject.toml`**: Deleted individual `pyproject.toml` files from `asset_core` and `crypto_single`.
- **Redundant `PYTHONPATH` Configuration**: Removed manual `PYTHONPATH` settings from `test-engine.sh` as it is now handled by the unified build system.

### Developer Experience
- **Simplified Dependency Management**: Developers now manage all dependencies from a single `pyproject.toml` file.
- **Improved Project Maintainability**: The unified structure makes it easier to manage configurations, run tests, and build the project.
- **Cleaner Codebase**: The flattened module structure and centralized testing improve code organization and readability.

---

### Git Commit Reference
- Main Change: [f7715db](https://github.com/tommot20077/tradingview-chart/commit/f7715db8581bdd8376967b383578d7b85e84e95e) - refactor(build): unify project structure and migrate to setuptools

## [asset-core 0.1.2] - 2025-06-29

### Added
- **End-to-End (E2E) Test Suite**:
  - `test_data_flow_integration.py`: Tests the complete data flow from data providers through the event system to the storage repository.
  - `test_system_resilience.py`: Tests system resilience and recovery under stress conditions like failures, disconnections, and resource exhaustion.
- **Performance Test Suite**:
  - `test_model_performance.py`: Benchmarks serialization, validation performance, and memory footprint of `Trade` and `Kline` models with large-scale data.
  - `test_concurrency_performance.py`: Evaluates the concurrency performance and thread safety of models in multi-threaded and asynchronous environments.
- **Security Test Suite**:
  - `test_input_sanitization.py`: Validates the system's defenses against malicious inputs, including SQL injection, XSS, and path traversal.
  - `test_sensitive_data_handling.py`: Ensures that sensitive data such as API keys and personal information are correctly masked in logs and outputs.

### Changed
- **Test Engine (`test-engine.sh`)**:
  - **Enhanced Path Handling**: Automatically normalizes test paths, supporting running tests for specific modules from the project root (e.g., `./run.sh test src/asset_core/tests/units`).
  - **Path Validation**: Added validation for test path formats with clear error messages to guide users.
  - **Automatic PYTHONPATH Configuration**: Automatically adds all modules under `src` to `PYTHONPATH` before test execution, simplifying import statements in tests.
- **Test Code Readability**:
  - Simplified all test import paths within the `asset_core` module from `from src.asset_core.asset_core...` to `from asset_core...`, improving code clarity.
- **Test Documentation**:
  - Added detailed docstrings conforming to project standards for all new E2E, performance, and security test cases, explaining their scope, preconditions, steps, and expected outcomes.

### Fixed
- **Import Path Issues**: Resolved the issue where `import asset_core` could not be used directly in `asset_core` tests, making the test environment more consistent with the actual runtime environment.

### Developer Experience
- **Testing Convenience**: Developers can now specify test targets more intuitively and receive clearer guidance.
- **Code Quality**: The expanded test coverage significantly enhances system stability, performance, and security.
- **Code Consistency**: Simplified import paths make the test code more standardized and easier to maintain.

---

### Git Commit Reference
- Main Change: [3c559fd](https://github.com/tommot20077/tradingview-chart/commit/3c559fd1bb30af37659887f999e9769eb9f6cd58) - feat(testing): enhance test engine and expand test coverage

## [asset-core 0.1.1] - 2025-06-27

### Added
- **Complete Project Documentation**: Established a developer guide.
  - Four core architectural principles (Layered Architecture, Unidirectional Dependency, Separation of Concerns, Configuration Unity).
  - Comprehensive `uv` tool command cheatsheet.
  - Development rules and testing requirements specification.
  - Git commit conventions and security guidelines.
- **Advanced Storage Test Suite**: Added tests for advanced storage features.
  - Data gap detection and compensation mechanism tests.
  - TTL support and expiration mechanism validation.
  - Batch operation performance tests.
- **`crypto_single` Application Foundation**: Created the first concrete application.
  - Module for cryptocurrency trade data processing.
  - Application-layer configuration and initialization logic.

### Changed
- **Improved Data Model Precision**: Enhanced the `Kline` model.
  - Expanded time interval support to include more standard trading timeframes.
  - Strengthened data validation logic to ensure price and volume consistency.
  - Improved time-series handling to increase historical data query efficiency.
- **Optimized Observability System**: Upgraded logging and monitoring functions.
  - Enhanced structured logging format to improve debugging experience.
  - Expanded trace context propagation to support more complex distributed scenarios.
  - Improved metrics collection precision for more accurate performance monitoring.
- **Strengthened Exception Handling**: Enhanced error handling and recovery capabilities.
  - Enriched error classification system for more precise error diagnosis.
  - Enhanced error context information to include more debugging details.
  - Improved automatic recovery mechanisms to increase system stability.
- **Simplified Configuration System**: Removed redundant configuration options.
  - Streamlined configuration module comments for better readability.
  - Unified configuration validation logic to reduce configuration errors.
  - Improved configuration inheritance mechanism to simplify application-layer configuration.

### Fixed
- **Unified Code Style**: Standardized code format across the project.
  - Unified import statement sorting and grouping rules.
  - Standardized variable naming and function definition styles.
  - Improved code comments and docstring formats.
- **Enhanced Test Coverage**: Improved test quality and coverage.
  - Expanded integration test scenarios to cover more real-world use cases.
  - Strengthened property-based testing strategies to ensure data model consistency.
  - Improved test assertion logic for more accurate error localization.

### Developer Experience
- **Documentation Integrity**: Developers now have a complete project development guide.
- **Code Consistency**: A unified code format improves team collaboration efficiency.
- **Maintenance Convenience**: A simplified configuration system reduces maintenance complexity.
- **Test Reliability**: An enhanced test suite ensures system stability.

---

### Git Commit Reference
- Main Change: [c1ff891](https://github.com/tommot20077/tradingview-chart/commit/c1ff8911ab0adf9cb75874a282d1715da8561a0c) - docs: add complete project documentation and improve code format

## [0.1.0] - 2025-06-26

### Added
- **Core Trading Data Infrastructure**: Established a complete financial data processing platform.
- **Complete Data Model System**: Professional-grade financial data structures.
- **Enterprise-Grade Observability Platform**: Comprehensive system monitoring and debugging.
- **High-Performance Storage Abstraction Layer**: Flexible data persistence solution.

### Core Functional Modules
- **Configuration Management System**: Unified configuration framework based on Pydantic.
- **Event System**: Type-safe event handling architecture.
- **Network Communication Layer**: Stable WebSocket connection management.
- **Exception Handling Framework**: Hierarchical error management.

### Development and Operations Support
- **Complete CI/CD Pipeline**: Automated development workflow.
- **Developer Tool Ecosystem**: A full toolchain to enhance development efficiency.
- **Testing Framework**: Multi-level quality assurance system.

### Design Patterns and Best Practices
- **Architectural Principles**: Ensuring system scalability and maintainability.
- **Code Quality**: Adherence to modern Python development standards.

### Examples and Documentation
- **Practical Code Examples**: Demonstrating best usage practices.
- **Complete Installation Guide**: Detailed environment setup instructions.

### Technical Features
- **Modern Architecture**: Utilizes the latest Python technology stack.
- **Enterprise-Grade Stability**: Complete error handling and recovery mechanisms.
- **High-Performance Design**: Optimized for asynchronous processing and batch operations.
- **Scalability Considerations**: Modular design supports future functional extensions.
- **Monitoring-Friendly**: Comprehensive observability support for production environments.

### Developer Impact
- **Modern Toolchain**: Provides full support for development, testing, and deployment.
- **Clear Architectural Guidance**: Layered design principles ensure clear code organization.
- **Rich Examples**: Practical code examples accelerate development.
- **Complete Test Coverage**: Multi-level testing ensures code quality.
- **Flexible Extension Mechanism**: Supports various custom requirements and future extensions.

---

### Git Commit Reference
- Main Change: [cf44928](https://github.com/tommot20077/tradingview-chart/commit/cf4492823362be226c022de17831cfcbad89a44b) - feat: re-architect testing framework and modernize core system