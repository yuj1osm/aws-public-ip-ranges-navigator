# Python Coding Guidelines

## Style

- Follow **PEP 8**. Use 4-space indentation and aim for lines of 88–99 characters.
- Naming: `snake_case` for functions and variables, `CONSTANT_CASE` for constants, `PascalCase` for classes.
- Group imports as standard library → third-party → local, separated by blank lines. Never use wildcard `import *`.

## Pythonic style

- Prefer comprehensions over building lists in a loop, but fall back to a plain loop when it gets complex.

## Data structures

- Use `@dataclass` for structured data; add `frozen=True` when it should be immutable.

## Error handling

- Avoid swallowing errors with a bare `except Exception:`; catch specific exceptions.
- Organize exceptions into custom classes so callers can branch on the type.
- Guarantee cleanup with `try/finally` or `with`.

## ディレクトリ構成

```
aws-public-ip-ranges-navigator/
├── src/
├── tests/
└── .kiro/specs/
```