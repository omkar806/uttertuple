# Contributing

When contributing to this repository, please ensure you follow these guidelines:

## Alembic Revisions

If you make any changes to the database models, you must create a new Alembic revision. You can do this by running the following command:

```bash
make add-alembic-revision
```

This will auto-generate a new revision file for your database schema changes.

## Pre-commit Hooks

Before committing your changes, please make sure that all pre-commit hooks are passing. You can run the hooks with the following command:

```bash
make pre-commit
```

This will run a series of checks to ensure code quality and consistency.

## Python Dependencies

If you add or update any Python dependencies, you need to synchronize the `requirements.in` file. You can do this by running:

```bash
make sync-uv-dependencies
```

This will update the `requirements.in` file based on `requirements.txt`. After that, you should run `make install-dependencies` to install the new dependencies.

## Running Tests

To ensure that your changes do not break any existing functionality, please run the test suite before submitting a pull request. You can run the tests with the following command:

```bash
make tests
```

## Merge Request Template Compliance

Before submitting a merge request, you must ensure that all items in the merge request template checklist are completed. The template is located at `.gitlab/merge_request_templates/Default.md` and will be automatically applied when creating a new merge request.

**Required checklist items include:**

### Core Requirements
- Clear explanation of changes and their purpose
- Tests written/updated for core changes
- All tests pass locally (`make tests`)
- No duplicate merge requests for the same changes
- Feature branch follows naming guidelines

### Contributing Requirements
- **Alembic**: Create new revision if database models changed (`make add-alembic-revision`)
- **Pre-commit**: All hooks must pass (`make pre-commit`)
- **Dependencies**: Sync and install if Python dependencies changed (`make sync-uv-dependencies` then `make install-dependencies`)
- **Security**: No hardcoded sensitive information

**All checklist items must be checked before requesting a review.** Incomplete checklists may result in delayed or rejected merge requests.

## Sensitive Information

Do not hardcode sensitive information such as API keys, secrets, or passwords in the source code. Use environment variables or a configuration file (e.g., `.env`) to manage these values. Refer to `env_sample` for the required environment variables.
