# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [asset-core 0.2.2] - 2025-07-05

### Enhanced

- **Comprehensive Test Framework**: Massive expansion of test coverage across all test
  categories
    - Added extensive integration tests for config, models, network, and observability
      components
    - Enhanced unit test coverage with new test modules for core functionality
    - Improved test organization and structure for better maintainability
- **Core Architecture Refinement**: Comprehensive improvements across the entire
  asset_core system
    - Enhanced code documentation with improved ABOUTME comments
    - Refined model implementations with better validation and error handling
    - Optimized configuration management and observability components

### Improved

- **Code Quality**: Extensive code formatting and style improvements across 118 files
    - Standardized code formatting and import organization
    - Enhanced readability through consistent styling
    - Improved docstrings and inline documentation
- **Test Infrastructure**: Significant enhancements to testing capabilities
    - Added contract tests for data providers, event bus, and storage repositories
    - Enhanced test configuration and helper utilities
    - Improved test coverage reporting and analysis

### Infrastructure

- **Project Configuration**: Updated build and development configurations
    - Enhanced `pyproject.toml` with updated dependencies
    - Improved `.gitignore` rules for better file management
    - Version bump to 0.2.2 with updated package metadata

### Developer Experience

- **Enhanced Testing**: Developers now have access to comprehensive test suites covering
  all aspects of the system
- **Better Code Organization**: Improved code structure and documentation make the
  codebase more accessible
- **Development Tools**: Enhanced tooling support for testing and development workflows

### Git Commit Reference

- Main
  Change: [18275b1](https://github.com/tommot20077/tradingview-chart/commit/18275b15287bb79ddecd0e6ac89ee9e9e640f4b7) -
    feat(tests): enhance test coverage and refine core architecture

---

## [asset-core 0.2.1] - 2025-07-02

### Added

- **Missing Unit Tests**: Added comprehensive unit tests for previously untested
  components:
    - `tests/asset_core/units/network/test_ws_client.py`: WebSocket client unit tests
    - `tests/asset_core/units/observability/test_logging.py`: Logging system unit tests
    - `tests/asset_core/units/observability/test_metrics.py`: Metrics system unit tests
- **Test Coverage Analysis**: Added detailed analysis documentation (`missing_tests.md`,
  `missing_tests_analysis.md`) identifying missing test cases and test categorization
  suggestions

### Enhanced

- **Core Architecture**: Comprehensive improvements across all asset_core modules (31
  files modified)
- **Code Documentation**: Enhanced ABOUTME comments and inline documentation throughout
  the codebase
- **Test Framework**: Significant updates to existing test suites with improved coverage
  and reliability
- **Build Configuration**: Updated project dependencies and development tooling
  configuration

### Improved

- **Code Quality**: Extensive refactoring and code formatting improvements across 91
  files
- **Test Organization**: Better categorization of unit vs integration tests
- **Error Handling**: Enhanced exception handling and validation throughout the system
- **Performance**: Optimized data models and observability components

### Infrastructure

- **Project Structure**: Continued refinement of the unified monorepo structure
- **Testing Tools**: Enhanced test engine with improved path handling and validation
- **Development Workflow**: Improved build scripts and dependency management
- 
### Git Commit Reference

- Main
  Change: [d813359](https://github.com/tommot20077/tradingview-chart/commit/d81335998cd50c161d3030350849fc12cf3cbd16) -
  feat(core): enhance test coverage and refine core architecture

---

## [crypto-single 0.1.1] - 2025-07-03

### Refactored

- **Configuration System**: Overhauled the `SingleCryptoSettings` class, introducing
  extensive validation rules for nearly every configuration parameter, especially for
  production environments. This includes strict checks for database URLs, secret keys,
  and API credentials.
- **Testing Infrastructure**: Restructured the entire testing suite by moving all tests
  to a root-level `tests/` directory and removing all contract tests from the
  `crypto_single` module. This simplifies the project structure and aligns with standard
  practices.
- **CI/CD Pipeline**: Enhanced the GitHub Actions workflow (`ci.yml`) to support manual
  triggers (`workflow_dispatch`), multi-version Python testing (3.8-3.12), and selective
  test execution (e.g., unit, integration, quality-only).
- **Test Execution Scripts**: Simplified `run.sh` and `test-engine.sh` to directly use
  `pytest` for test execution, removing complex module detection logic and improving
  readability.

### Added

- **Comprehensive Unit Tests**: Added a significant number of new unit tests for
  `asset_core`, covering previously untested areas such as `ws_client`, `logging`,
  `metrics`, and `storage` repositories.
- **Enhanced Security Validation**: Implemented numerous security-focused validators for
  configuration settings, ensuring that production environments adhere to strict
  security standards.

### Removed

- **Legacy Test Files**: Deleted all contract and unit tests from
  `src/crypto_single/tests/`, which have been replaced by the new, more comprehensive
  tests in the root `tests/` directory.
- **Old Configuration Backups**: Removed `pyproject_backup.toml` and
  `pyproject_old.toml` to clean up the project root.

### Developer Experience

- **Improved Configuration Safety**: The new validation system provides developers with
  immediate feedback on configuration errors, reducing runtime issues.
- **Flexible and Faster CI**: Developers can now manually trigger specific tests on
  specific Python versions, speeding up the development and validation cycle.
- **Simplified Project Navigation**: The new test structure makes it easier to locate
  and manage tests for different parts of the application.

### Git Commit Reference

- Main
  Change: [ad1fc02](https://github.com/tommot20077/tradingview-chart/commit/ad1fc021270dbf48fdfe75f4a481118be0bb9be1) -
  refactor(config): overhaul configuration system and enhance testing infrastructure

---

## [asset-core 0.2.0] - 2025-06-29

### Changed

- **Unified Project Structure**: Migrated the entire project to a unified monorepo
  structure managed by a single root `pyproject.toml` and `setuptools`.
- **Simplified Module Layout**: Flattened the directory structure for `asset_core` and
  `crypto_single` from a nested (`module/module`) to a single-level (`module`) layout,
  resulting in cleaner import paths.
- **Centralized Dependencies**: Consolidated all project dependencies into the root
  `pyproject.toml`, using `project.optional-dependencies` to manage dependencies for
  different applications and development.
- **Unified Test Directory**: Moved all tests to a root-level `tests/` directory,
  organized by module, for centralized test management and execution.

### Removed

- **Module-specific `pyproject.toml`**: Deleted individual `pyproject.toml` files from
  `asset_core` and `crypto_single`.
- **Redundant `PYTHONPATH` Configuration**: Removed manual `PYTHONPATH` settings from
  `test-engine.sh` as it is now handled by the unified build system.

### Developer Experience

- **Simplified Dependency Management**: Developers now manage all dependencies from a
  single `pyproject.toml` file.
- **Improved Project Maintainability**: The unified structure makes it easier to manage
  configurations, run tests, and build the project.
- **Cleaner Codebase**: The flattened module structure and centralized testing improve
  code organization and readability.

### Git Commit Reference

- Main
  Change: [f256589](https://github.com/tommot20077/tradingview-chart/commit/f2565896bf4998165c7296bb1cc7cf8d9d30f996) -
  refactor(build): unify project structure and migrate to setuptools

---

## [asset-core 0.1.2] - 2025-06-29

### Added

- **End-to-End (E2E) Test Suite**:
    - `test_data_flow_integration.py`: Tests the complete data flow from data providers
      through the event system to the storage repository.
    - `test_system_resilience.py`: Tests system resilience and recovery under stress
      conditions like failures, disconnections, and resource exhaustion.
- **Performance Test Suite**:
    - `test_model_performance.py`: Benchmarks serialization, validation performance, and
      memory footprint of `Trade` and `Kline` models with large-scale data.
    - `test_concurrency_performance.py`: Evaluates the concurrency performance and
      thread safety of models in multi-threaded and asynchronous environments.
- **Security Test Suite**:
    - `test_input_sanitization.py`: Validates the system's defenses against malicious
      inputs, including SQL injection, XSS, and path traversal.
    - `test_sensitive_data_handling.py`: Ensures that sensitive data such as API keys
      and personal information are correctly masked in logs and outputs.

### Changed

- **Test Engine (`test-engine.sh`)**:
    - **Enhanced Path Handling**: Automatically normalizes test paths, supporting
      running tests for specific modules from the project root (e.g.,
      `./run.sh test src/asset_core/tests/units`).
    - **Path Validation**: Added validation for test path formats with clear error
      messages to guide users.
    - **Automatic PYTHONPATH Configuration**: Automatically adds all modules under `src`
      to `PYTHONPATH` before test execution, simplifying import statements in tests.
- **Test Code Readability**:
    - Simplified all test import paths within the `asset_core` module from
      `from src.asset_core.asset_core...` to `from asset_core...`, improving code
      clarity.
- **Test Documentation**:
    - Added detailed docstrings conforming to project standards for all new E2E,
      performance, and security test cases, explaining their scope, preconditions,
      steps, and expected outcomes.

### Fixed

- **Import Path Issues**: Resolved the issue where `import asset_core` could not be used
  directly in `asset_core` tests, making the test environment more consistent with the
  actual runtime environment.

### Developer Experience

- **Testing Convenience**: Developers can now specify test targets more intuitively and
  receive clearer guidance.
- **Code Quality**: The expanded test coverage significantly enhances system stability,
  performance, and security.
- **Code Consistency**: Simplified import paths make the test code more standardized and
  easier to maintain.

### Git Commit Reference

- Main
  Change: [97b3b04](https://github.com/tommot20077/tradingview-chart/commit/97b3b047bab3652db013ea8d28585899d289498e) -
  feat(testing): enhance test engine and expand test coverage

---

## [asset-core 0.1.1] - 2025-06-27

### Added

- **Complete Project Documentation**: Established a developer guide.
    - Four core architectural principles (Layered Architecture, Unidirectional
      Dependency, Separation of Concerns, Configuration Unity).
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
- **Strengthened Exception Handling**: Enhanced error handling and recovery
  capabilities.
    - Enriched error classification system for more precise error diagnosis.
    - Enhanced error context information to include more debugging details.
    - Improved automatic recovery mechanisms to increase system stability.
- **Simplified Configuration System**: Removed redundant configuration options.
    - Streamlined configuration module comments for better readability.
    - Unified configuration validation logic to reduce configuration errors.
    - Improved configuration inheritance mechanism to simplify application-layer
      configuration.

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
- **Maintenance Convenience**: A simplified configuration system reduces maintenance
  complexity.
- **Test Reliability**: An enhanced test suite ensures system stability.

### Git Commit Reference

- Main
  Change: [c1ff891](https://github.com/tommot20077/tradingview-chart/commit/c1ff8911ab0adf9cb75874a282d1715da8561a0c) -
  docs: add complete project documentation and improve code format

---

## [asset-core 0.1.0] - 2025-06-26

### Added

- **Core Trading Data Infrastructure**: Established a complete financial data processing
  platform.
- **Complete Data Model System**: Professional-grade financial data structures.
- **Enterprise-Grade Observability Platform**: Comprehensive system monitoring and
  debugging.
- **High-Performance Storage Abstraction Layer**: Flexible data persistence solution.

### Core Functional Modules

- **Configuration Management System**: Unified configuration framework based on
  Pydantic.
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
- **High-Performance Design**: Optimized for asynchronous processing and batch
  operations.
- **Scalability Considerations**: Modular design supports future functional extensions.
- **Monitoring-Friendly**: Comprehensive observability support for production
  environments.

### Developer Impact

- **Modern Toolchain**: Provides full support for development, testing, and deployment.
- **Clear Architectural Guidance**: Layered design principles ensure clear code
  organization.
- **Rich Examples**: Practical code examples accelerate development.
- **Complete Test Coverage**: Multi-level testing ensures code quality.
- **Flexible Extension Mechanism**: Supports various custom requirements and future
  extensions.

### Git Commit Reference

- Main
  Change: [cf44928](https://github.com/tommot20077/tradingview-chart/commit/cf4492823362be226c022de17831cfcbad89a44b) -
  feat: re-architect testing framework and modernize core system