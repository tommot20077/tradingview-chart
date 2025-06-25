# TradingChart Examples

This directory contains usage examples for the TradingChart system components.

## Examples Overview

### 1. Custom Provider Implementation
- `custom_provider.py` - How to implement a custom data provider
- Shows how to extend `AbstractDataProvider` for new exchanges

### 2. Custom Storage Implementation  
- `custom_storage.py` - How to implement custom storage backends
- Examples for different database types and storage strategies

### 3. Event System Usage
- `event_system_example.py` - How to use the event system
- Publishing, subscribing, and filtering events

### 4. Configuration Examples
- `configuration_example.py` - How to configure applications
- Environment-specific configurations and validation

## Getting Started

Each example is self-contained and includes:
- Clear documentation of the use case
- Complete implementation example
- Test cases demonstrating usage
- Configuration examples

## Running Examples

Make sure you have the development environment set up:

```bash
# Install dependencies
./setup.sh

# Run a specific example
cd examples
python custom_provider.py
```

## Contributing Examples

When adding new examples:
1. Follow the existing structure and documentation style
2. Include comprehensive docstrings
3. Add test cases where appropriate
4. Update this README with the new example