## Core Principles

This project is built upon the following four core principles, which should guide all
development decisions:

1. **Layered Architecture**
    - Independent applications (e.g., `crypto_single`, `crypto_cluster`) are built upon
      a
      shared foundational library (`asset_core`).

2. **Unidirectional Dependency**
    - Dependencies flow strictly in one direction: **Application Layer → Core Layer**.
    - The `asset_core` library **must never** import from any application layer module.

3. **Separation of Concerns**
    - `asset_core` provides abstract interfaces, common models, and utilities.
    - Concrete business logic is implemented in the application layers (e.g.,
      `crypto_single`).

4. **Configuration Unity**
    - All configuration settings are managed centrally through Pydantic models.
    - Application-layer configuration models must inherit from the base configuration
      models
      defined in `asset_core`.

## Command Cheatsheet

This project uses `uv` as the sole package and environment manager. All Python-related
commands should be executed via `uv`.

Instead of using `python` directly, please make sure to use `uv run python3` to ensure
the correct

### 1. Project Setup

| Task                    | Command                  | Description                                                   |
|:------------------------|:-------------------------|:--------------------------------------------------------------|
| **First-Time Install**  | `./setup.sh`             | Installs all core, application, and development dependencies. |
| **Core Only Install**   | `./setup.sh --core-only` | Installs only `asset_core` and its dependencies.              |
| **Apps Only Install**   | `./setup.sh --apps-only` | Installs only applications and their dependencies.            |
| **Update Dependencies** | `./run.sh install`       | Updates/installs dependencies based on `pyproject.toml`.      |

### 2. Daily Development

| Task                    | Command                                                         | Description                                                     |
|:------------------------|:----------------------------------------------------------------|:----------------------------------------------------------------|
| **Check Status**        | `./run.sh status`                                               | Displays a summary of the project environment and dependencies. |
| **Run Single Service**  | `./run.sh single [args]`                                        | Starts the `crypto_single` application.                         |
| **Run Cluster Service** | `./run.sh cluster [args]`                                       | Starts the `crypto_cluster` application.                        |
| **Direct Execution**    | `uv run --directory src/crypto_single python3 -m crypto_single` | Runs without activating the venv (not recommended).             |

### 3. Quality Assurance

| Task                        | Command                                         | Description                                                     |
|:----------------------------|:------------------------------------------------|:----------------------------------------------------------------|
| **Run All Tests + QA**      | `./run.sh test`                                 | Runs all tests with quality checks (linting, format, mypy) and coverage. |
| **Run Tests Only**          | `./run.sh test --skip-quality-checks`          | Runs tests without quality checks (faster for development).     |
| **Run Quality Checks Only** | `./run.sh lint`                                 | Executes formatting, linting, and type checking only.          |
| **Fast Unit Tests**         | `./run.sh test units --skip-quality-checks --parallel-units=4 --no-cov` | Fastest unit test execution for development. |
| **Run Specific Test**       | `./run.sh test <path_to_test_file>`             | Runs specific test file/directory with quality checks.         |
| **Format Code**             | `uv run ruff format .`                          | Format code only.                                               |
| **Lint Code**               | `uv run ruff check .`                           | Lint code only.                                                 |
| **Type Check**              | `uv run mypy .`                                 | Type checking only.                                             |

### 4. Dependency Management

| Task                           | Command                                            |
|:-------------------------------|:---------------------------------------------------|
| **Add Dependency to Core**     | `cd src/asset_core && uv add "package-name"`       |
| **Add Dev Dependency to Core** | `cd src/asset_core && uv add --dev "package-name"` |
| **Add Dependency to App**      | `cd src/crypto_single && uv add "package-name"`    |

## Development Rules and Standards

### Core Library (`asset_core`) Modification Rule

- The `asset_core` library is the foundation of the project and must remain stable.
- **Rule**: Modifications to `asset_core` are strictly prohibited unless explicitly
  stated as a required task. Under all other circumstances, you must not alter its
  contents.

### Testing Requirements

- **Rule**: All concrete implementations in application layers (e.g., `crypto_single`,
  `crypto_cluster`) **must** be accompanied by comprehensive unit tests.
- Tests must cover:
- **Normal cases**: Expected inputs and successful outcomes.
- **Error cases**: How the code handles exceptions and invalid inputs.
- **Edge cases**: Boundary values, empty inputs, and other corner-case scenarios.

- **Format**: Please follow the struction below for tests docstrings:

```markdown
Summary line.

Description of what the test covers.

Preconditions:
    - List any required setup
  
Steps:
    - List key steps (if not clear from code)

Expected Result:
    - What should happen
```

- **Very Important**: After writing tests, please run them using `./run.sh test path_of_the_modify_file` to ensure they pass before committing any changes. The test command now includes quality checks (linting, format checking, type checking) by default to ensure code quality. Use `--skip-quality-checks` for faster development cycles when needed.

### Code Standards

- **Language**: All comments, documentation, and variable names must be in **English**.
- **Type Hints**: **Required** for all function signatures.
- **Docstrings**: **Required** for all public modules, classes, and functions.
- **Terminology**: When explaining in comments or docs, the English term "symbol"
  corresponds to "交易代碼" in Chinese.
- **Type Definitions**:
    - Common types are already defined in `core/types`
    - Strictly adhere to the defined specifications
    - When using Pydantic Annotated, combine with Pydantic models or `@validate_call`
      decorator

## Git Commit Convention

This project strictly follows the **Conventional Commits** v1.0.0 specification. This
practice facilitates automated versioning and changelog generation.

Before committing, ensure your code passes all quality checks. The `./run.sh test` command now automatically runs formatting, linting, and type checking before executing tests, ensuring comprehensive code quality validation.

#### Format

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

#### Common Types (`<type>`)

| Type       | Description                                                   |
|:-----------|:--------------------------------------------------------------|
| `feat`     | A new feature                                                 |
| `fix`      | A bug fix                                                     |
| `docs`     | Documentation only changes                                    |
| `style`    | Code style adjustments (formatting, white-space)              |
| `refactor` | A code change that neither fixes a bug nor adds a feature     |
| `perf`     | A code change that improves performance                       |
| `test`     | Adding missing tests or correcting existing tests             |
| `build`    | Changes that affect the build system or external dependencies |
| `ci`       | Changes to CI/CD configuration files and scripts              |
| `chore`    | Other changes that don't modify `src` or `test` files         |

#### Example Commits

**Simple Commit**:

```
feat(api): add new endpoint for symbol validation
```

**Commit with Detailed Body**:

```
fix(provider): correct timestamp parsing for OKX websocket stream

The previous implementation failed to handle millisecond precision,
causing data alignment issues. This commit adjusts the parsing logic
to correctly handle unix timestamps with milliseconds.
```

## Security Notes

- **Configuration Management**: Sensitive information (e.g., API keys) must be managed
  via **environment variables**.
- **Log Safety**: **Never** log any API keys, passwords, or secrets.
- **Data Validation**: All external input data must be strictly validated using *
  *Pydantic models**.
- **Dependency Locking**: The `uv.lock` file locks all dependency versions for
  reproducible builds and must be committed to version control.

      
    
      