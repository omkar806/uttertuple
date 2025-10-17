# Template Repo

## Prerequisites
- Docker 28.3.3 or higher installed and running
- Docker Compose v2.39.2 or higher installed and running
- Python 3.11 or higher
- Node.js v23.9.0 or higher

## Quick Start

### Option 1: Docker (Recommended)
```bash
# macOS/Linux
make start-dev      # Start application using terminal, similar for prod
make stop-dev       # Stop application using terminal,  similar for prod

# Windows
.\build.ps1 start-dev    # Start application using powershell, similar for prod
.\build.ps1 stop-dev     # Stop application using powershell, similar for production
```

### Cleanup Commands
```bash
# macOS/Linux
make clean-dev             # Clean up development containers, volumes, and networks
make clean-prod            # Clean up production containers, volumes, and networks

# Windows
.\build.ps1 clean-dev      # Clean up development containers, volumes, and networks
.\build.ps1 clean-prod     # Clean up production containers, volumes, and networks
```

### Option 2: Local Development
First, create and activate a Python virtual environment:

```bash
# Create virtual environment
python3 -m venv myenv

# Activate (macOS/Linux)
source myenv/bin/activate

# Activate (Windows)
myenv\Scripts\activate
```

Then start the application:
```bash
# macOS/Linux
make run-application     # Start all components using terminal
make stop-application    # Stop all components using terminal

# Windows 
.\build.ps1 run-application    # Start all components using powershell
.\build.ps1 stop-application   # Stop all components using powershell
```

Use `CUSTOM_OAUTH_BOOTSTRAP_ADMIN_EMAIL` and `CUSTOM_OAUTH_BOOTSTRAP_ADMIN_PASSWORD` from `/bot_service/src/backend/etc/.env` variables as ADMIN credentials for login

## SMTP Configuration
To enable email functionalities, configure the SMTP settings in the `.env` file located at `/bot_service/src/backend/etc/.env`. Set the following variables:
- `SMTP_HOST`: Your SMTP server address
- `SMTP_PORT`: Your SMTP server port
- `SMTP_USERNAME`: Your SMTP username
- `SMTP_PASSWORD`: Your SMTP password
- `SMTP_FROM_EMAIL`: The email address from which emails will be sent
- `SMTP_FROM_NAME`: The name that will appear as the sender
- `SMTP_USE_TLS`: Set to `true` if your SMTP server requires TLS, otherwise `false`
- `PROXY_URL`: Application's public URL, used in email links for password resets and notifications. Default is localhost.

Ensure these settings are correctly configured to enable email functionalities such as password resets and notifications.

## Development Commands

### Documentation
```bash
# macOS/Linux
make docs           # Serve docs locally
make deploy-docs    # Deploy to GitHub Pages

# Windows
.\build.ps1 docs         # Serve docs locally
.\build.ps1 deploy-docs  # Deploy to GitHub Pages
```

### Code Quality
```bash
# macOS/Linux
make pre-commit     # Run pre-commit hooks

# Windows
.\build.ps1 pre-commit   # Run pre-commit hooks
```

### Database Migrations (Alembic)
```bash
# macOS/Linux
make add-alembic-revision      # Create new migration
make upgrade-alembic-revision  # Apply migrations
make show-alembic-history      # View migration history

# Windows
.\build.ps1 add-alembic-revision      # Create new migration
.\build.ps1 upgrade-alembic-revision  # Apply migrations
.\build.ps1 show-alembic-history      # View migration history
```

### Dependency Management
```bash
# macOS/Linux
make sync-uv-dependencies    # Update dependency file
make install-dependencies    # Install all dependencies

# Windows
.\build.ps1 sync-uv-dependencies    # Update dependency file
.\build.ps1 install-dependencies    # Install all dependencies
```


### Testing
```bash
# macOS/Linux
make tests          # Run test suite

# Windows
.\build.ps1 tests   # Run test suite
```

### Docker Utilities
```bash
# macOS/Linux
make clean-docker-cache    # Clean Docker cache
make list-services         # List running services

# Windows
.\build.ps1 clean-docker-cache    # Clean Docker cache
.\build.ps1 list-services         # List running services
```


## Available Commands
For a complete list of available commands, run:
```bash
# macOS/Linux
make help

# Windows
.\build.ps1 help
```

## Notes
- Ensure `.env` files are properly configured before starting the application
- Run `clean-docker-cache` periodically to free up disk space
- Always run database migrations after updating the codebase