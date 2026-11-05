# Contributing

## Workflow

- Use `develop` for integration work.
- Open pull requests from feature branches into `develop`.
- Promote validated changes from `develop` to `main`.
- Keep pull requests focused and describe behavior, tests, and operational impact.

## Before implementation

Check [docs/PROJECT_BRIEF.md](docs/PROJECT_BRIEF.md) and record material architecture decisions before introducing runtime-specific files.

## Quality expectations

- Add tests for behavior changes.
- Never commit credentials, tokens, personal data, or production datasets.
- Keep configuration explicit and provide safe examples without real secrets.
- Document required environment variables and operational changes.
