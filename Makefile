GIT_ROOT := $(shell git rev-parse --show-toplevel 2>/dev/null || pwd)
DEV_GIT_BRANCH := main
PROD_GIT_BRANCH := prod
PROJECT_NAME := $(shell basename $(GIT_ROOT) | tr '[:upper:]' '[:lower:]')

.PHONY: help \
	docs deploy-docs \
	pre-commit \
	init-alembic add-alembic-revision upgrade-alembic-revision downgrade-alembic-revision show-alembic-history show-alembic-current stamp-alembic-revision \
	create-volume destroy-volume create-network destroy-network stop-services start-services stop-dev-application start-dev-application stop-prod-application start-prod-application clean-docker-cache \
	list-services list-volumes list-dev-containers list-prod-containers \
	start-dev stop-dev start-prod stop-prod clean-dev clean-prod \
	sync-uv-dependencies install-dependencies \
	tests \
	run-application-backend run-application-worker run-application-frontend run-application stop-application \
	create-sample-env dev-available-at prod-available-at

# ANSI color codes
GREEN  := \033[0;32m
YELLOW := \033[0;33m
BLUE   := \033[0;34m
CYAN   := \033[0;36m
RESET  := \033[0m

help:
	@echo "${YELLOW}Available commands:${RESET}"
	@echo ""
	@echo "${CYAN}Documentation:${RESET}"
	@echo "  ${GREEN}docs                       ${RESET}: Generate local documentation in the /docs folder using MkDocs."
	@echo "  ${GREEN}deploy-docs                ${RESET}: Deploy the generated documentation to GitHub Pages."
	@echo ""
	@echo "${CYAN}Code Quality:${RESET}"
	@echo "  ${GREEN}pre-commit                 ${RESET}: Install and run pre-commit hooks for code quality checks."
	@echo "  ${GREEN}tests                      ${RESET}: Run tests using pytest."
	@echo ""
	@echo "${CYAN}Database Migrations (Alembic):${RESET}"
	@echo "  ${GREEN}init-alembic               ${RESET}: Initialize Alembic for database migrations."
	@echo "  ${GREEN}add-alembic-revision       ${RESET}: Auto-generate an Alembic revision for database migrations."
	@echo "  ${GREEN}upgrade-alembic-revision   ${RESET}: Upgrade the database schema to the latest Alembic revision."
	@echo "  ${GREEN}downgrade-alembic-revision ${RESET}: Downgrade the database schema by one revision."
	@echo "  ${GREEN}show-alembic-history       ${RESET}: Show the Alembic migration history."
	@echo "  ${GREEN}show-alembic-current       ${RESET}: Show the current Alembic revision."
	@echo "  ${GREEN}stamp-alembic-revision     ${RESET}: Stamp the database with the latest Alembic revision."
	@echo ""
	@echo "${CYAN}Docker Infrastructure:${RESET}"
	@echo "  ${GREEN}create-volume              ${RESET}: Create the required Docker volumes."
	@echo "  ${GREEN}destroy-volume             ${RESET}: Remove the Docker volumes."
	@echo "  ${GREEN}create-network             ${RESET}: Create the required Docker networks."
	@echo "  ${GREEN}destroy-network            ${RESET}: Remove the Docker networks."
	@echo "  ${GREEN}clean-docker-cache         ${RESET}: Prune Docker build cache and builder cache."
	@echo ""
	@echo "${CYAN}Docker Services:${RESET}"
	@echo "  ${GREEN}start-services             ${RESET}: Stop then start all services with rebuild in detached mode."
	@echo "  ${GREEN}stop-services              ${RESET}: Stop all running Docker services as defined in docker-compose-services.yml."
	@echo "  ${GREEN}list-services              ${RESET}: List all Docker services and their status."
	@echo "  ${GREEN}list-volumes               ${RESET}: List all Docker volumes."
	@echo ""
	@echo "${CYAN}Development Environment:${RESET}"
	@echo "  ${GREEN}start-dev                  ${RESET}: Start full development environment (services + application)."
	@echo "  ${GREEN}stop-dev                   ${RESET}: Stop full development environment (application + services)."
	@echo "  ${GREEN}start-dev-application      ${RESET}: Start the development instance of the application with rebuild."
	@echo "  ${GREEN}stop-dev-application       ${RESET}: Shut down the development instance of the application."
	@echo "  ${GREEN}list-dev-containers        ${RESET}: List all development Docker containers."
	@echo "  ${GREEN}clean-dev                  ${RESET}: Clean up development containers, volumes, and networks."
	@echo "  ${GREEN}dev-available-at           ${RESET}: Show all available development service URLs."
	@echo ""
	@echo "${CYAN}Production Environment:${RESET}"
	@echo "  ${GREEN}start-prod                 ${RESET}: Start full production environment (services + application)."
	@echo "  ${GREEN}stop-prod                  ${RESET}: Stop full production environment (application + services)."
	@echo "  ${GREEN}start-prod-application     ${RESET}: Start the production instance of the application with rebuild."
	@echo "  ${GREEN}stop-prod-application      ${RESET}: Stop the production instance of the application."
	@echo "  ${GREEN}list-prod-containers       ${RESET}: List all production Docker containers."
	@echo "  ${GREEN}clean-prod                 ${RESET}: Clean up production containers, volumes, and networks."
	@echo "  ${GREEN}prod-available-at          ${RESET}: Show all available production service URLs."
	@echo ""
	@echo "${CYAN}Dependencies:${RESET}"
	@echo "  ${GREEN}sync-uv-dependencies       ${RESET}: Synchronize the uv package dependencies by updating requirements."
	@echo "  ${GREEN}install-dependencies       ${RESET}: Install Python dependencies from requirements.txt for local run."
	@echo ""
	@echo "${CYAN}Local Development:${RESET}"
	@echo "  ${GREEN}run-application            ${RESET}: Start all application components locally in background."
	@echo "  ${GREEN}stop-application           ${RESET}: Stop all locally running application components."
	@echo "  ${GREEN}run-application-backend    ${RESET}: Run the application backend locally."
	@echo "  ${GREEN}run-application-worker     ${RESET}: Run the application worker locally."
	@echo "  ${GREEN}run-application-frontend   ${RESET}: Run the application frontend locally."
	@echo ""
	@echo "${CYAN}Utilities:${RESET}"
	@echo "  ${GREEN}create-sample-env          ${RESET}: Create sample .env files for backend, frontend & services."

# --- Miscellaneous ---
.SILENT: create-sample-env
create-sample-env:
	@echo "${YELLOW}Do you want to create sample .env file for the frontend, backend & common services? (y/n)${RESET}"; \
	read CREATE_ENV; \
	if [ "$$CREATE_ENV" = "y" ]; then \
		echo "${CYAN}Creating sample .env files for backend, frontend & common services ...${RESET}"; \
		[ -f ${GIT_ROOT}/bot_service/src/frontend/.env ] || cp ${GIT_ROOT}/bot_service/src/frontend/.env_sample ${GIT_ROOT}/bot_service/src/frontend/.env; \
		[ -f ${GIT_ROOT}/bot_service/src/backend/etc/.env ] || cp ${GIT_ROOT}/bot_service/src/backend/etc/.env_sample ${GIT_ROOT}/bot_service/src/backend/etc/.env; \
		[ -f ${GIT_ROOT}/.env ] || cp ${GIT_ROOT}/.env_services_sample ${GIT_ROOT}/.env; \
		echo "${GREEN}Sample .env files created successfully!${RESET}"; \
		echo "${CYAN}You can edit ${GIT_ROOT}/bot_service/src/backend/etc/.env to configure your environment.${RESET}"; \
		echo "${CYAN}You can edit ${GIT_ROOT}/bot_service/src/frontend/.env to configure your environment.${RESET}"; \
		echo "${CYAN}You can edit ${GIT_ROOT}/.env to configure your environment.${RESET}"; \
	else \
		echo "${YELLOW}Skipping .env file creation.${RESET}"; \
	fi

.SILENT: dev-available-at
dev-available-at:
	@echo "${CYAN}┌─────────────────────────────────────────────────────────────────┐${RESET}"
	@echo "${CYAN}│                    DEVELOPMENT ENVIRONMENT                      │${RESET}"
	@echo "${CYAN}└─────────────────────────────────────────────────────────────────┘${RESET}"
	@echo ""
	@echo "${CYAN}Application Services:${RESET}"
	@$(MAKE) list-services
	@echo ""
	@echo "${CYAN}Development Containers:${RESET}"
	@$(MAKE) list-dev-containers
	@echo ""
	@echo "${CYAN}─────────────────────────────────────────────────────────────────${RESET}"
	@echo "${YELLOW}Admin Credentials:${RESET}"
	@echo "  Email:    ${GREEN}CUSTOM_OAUTH_BOOTSTRAP_ADMIN_EMAIL${RESET} (from .env)"
	@echo "  Password: ${GREEN}CUSTOM_OAUTH_BOOTSTRAP_ADMIN_PASSWORD${RESET} (from .env)"
	@echo "  Config:   ${BLUE}${GIT_ROOT}/bot_service/src/backend/etc/.env${RESET}"
	@echo ""
	@echo "${YELLOW}Note: Ports and host settings may vary based on .env configuration${RESET}"
	@echo "${CYAN}─────────────────────────────────────────────────────────────────${RESET}"

.SILENT: prod-available-at
prod-available-at:
	@echo "${CYAN}┌─────────────────────────────────────────────────────────────────┐${RESET}"
	@echo "${CYAN}│                     PRODUCTION ENVIRONMENT                      │${RESET}"
	@echo "${CYAN}└─────────────────────────────────────────────────────────────────┘${RESET}"
	@echo ""
	@echo "${CYAN}Application Services:${RESET}"
	@$(MAKE) list-services
	@echo ""
	@echo "${CYAN}Production Containers:${RESET}"
	@$(MAKE) list-prod-containers
	@echo ""
	@echo "${CYAN}─────────────────────────────────────────────────────────────────${RESET}"
	@echo "${YELLOW}Admin Credentials:${RESET}"
	@echo "  Email:    ${GREEN}CUSTOM_OAUTH_BOOTSTRAP_ADMIN_EMAIL${RESET} (from .env)"
	@echo "  Password: ${GREEN}CUSTOM_OAUTH_BOOTSTRAP_ADMIN_PASSWORD${RESET} (from .env)"
	@echo "  Config:   ${BLUE}${GIT_ROOT}/bot_service/src/backend/etc/.env${RESET}"
	@echo ""
	@echo "${YELLOW}Note: Ports and host settings may vary based on .env configuration${RESET}"
	@echo "${CYAN}─────────────────────────────────────────────────────────────────${RESET}"

# --- Alembic Database Migrations ---
init-alembic:
	@echo "${BLUE}Initializing Alembic for database migrations...${RESET}"
	cd ${GIT_ROOT}/bot_service/src/backend && alembic init alembic

add-alembic-revision:
	@echo "${BLUE}Auto-generating an Alembic revision for database migrations...${RESET}"
	@echo "${YELLOW}Enter alembic commit message: ${RESET}"; \
	read ALEMBIC_COMMIT_MSG; \
	echo "${CYAN}Your alembic commit message is: $$ALEMBIC_COMMIT_MSG${RESET}"; \
	cd ${GIT_ROOT}/bot_service/src/backend && alembic revision --autogenerate -m "$$ALEMBIC_COMMIT_MSG"

upgrade-alembic-revision:
	@echo "${BLUE}Upgrading the database schema to the latest Alembic revision...${RESET}"
	cd ${GIT_ROOT}/bot_service/src/backend && alembic upgrade head

downgrade-alembic-revision:
	@echo "${BLUE}Downgrading the database schema by one revision...${RESET}"
	cd ${GIT_ROOT}/bot_service/src/backend && alembic downgrade -1

show-alembic-history:
	@echo "${BLUE}Showing the Alembic migration history...${RESET}"
	cd ${GIT_ROOT}/bot_service/src/backend && alembic history --verbose

show-alembic-current:
	@echo "${BLUE}Showing the current Alembic revision...${RESET}"
	cd ${GIT_ROOT}/bot_service/src/backend && alembic current

stamp-alembic-revision:
	@echo "${BLUE}Stamping the database with the latest Alembic revision...${RESET}"
	cd ${GIT_ROOT}/bot_service/src/backend && alembic stamp head

# --- Docker Management ---
create-volume:
	@echo "${CYAN}Creating Docker volumes...${RESET}"
	docker volume create postgres_data || true
	docker volume create pgadmin_data || true
	docker volume create redis_data || true

destroy-volume:
	@echo "${CYAN}Destroying Docker volumes...${RESET}"
	docker volume rm postgres_data || true
	docker volume rm pgadmin_data || true
	docker volume rm redis_data || true

create-network:
	@echo "${CYAN}Creating Docker networks...${RESET}"
	docker network create -d bridge shared_network || true

destroy-network:
	@echo "${CYAN}Destroying Docker networks...${RESET}"
	docker network rm shared_network || true

clean-docker-cache:
	@echo "${CYAN}Pruning Docker build cache and builder cache...${RESET}"
	docker buildx prune -a -f
	docker builder prune -a -f

.SILENT: list-services
list-services:
	@echo "${CYAN}Listing Docker services...${RESET}"
	@docker compose --project-name ${PROJECT_NAME} -f docker-compose-services.yml ps --format "table {{.Names}}\t\t{{.Ports}}" | awk 'NR==1 || /0\.0\.0\.0/ {print}' | sed 's/0\.0\.0\.0://g' | sed 's/->[^,]*//g' | sed 's/,.*//g' | sed 's/<no value>/NAMES/'

list-volumes:
	@echo "${CYAN}Listing Docker volumes...${RESET}"
	docker volume ls

.SILENT: list-dev-containers
list-dev-containers:
	@echo "${CYAN}Listing Docker development containers...${RESET}"
	@docker compose --project-name ${PROJECT_NAME}_${DEV_GIT_BRANCH} -f docker-compose-main.yml ps --format "table {{.Names}}\t\t{{.Ports}}" | awk 'NR==1 || /0\.0\.0\.0/ {print}' | sed 's/0\.0\.0\.0://g' | sed 's/->[^,]*//g' | sed 's/,.*//g' | sed 's/<no value>/NAMES/'

.SILENT: list-prod-containers
list-prod-containers:
	@echo "${CYAN}Listing Docker production containers...${RESET}"
	@docker compose --project-name ${PROJECT_NAME}_${PROD_GIT_BRANCH} -f docker-compose-prod.yml ps --format "table {{.Names}}\t\t{{.Ports}}" | awk 'NR==1 || /0\.0\.0\.0/ {print}' | sed 's/0\.0\.0\.0://g' | sed 's/->[^,]*//g' | sed 's/,.*//g' | sed 's/<no value>/NAMES/'

stop-services:
	@echo "${CYAN}Stopping Docker services...${RESET}"
	docker compose --project-name ${PROJECT_NAME} -f docker-compose-services.yml down

start-services: stop-services create-volume create-network
	@echo "${CYAN}Starting Docker services...${RESET}"
	docker compose --project-name ${PROJECT_NAME} -f docker-compose-services.yml up -d --build

stop-dev-application:
	@echo "${YELLOW}Shutting down the development instance of the application...${RESET}"
	docker compose --project-name ${PROJECT_NAME}_${DEV_GIT_BRANCH} -f docker-compose-main.yml down

start-dev-application: stop-dev-application
	@echo "${YELLOW}Starting the development instance of the application...${RESET}"
	docker compose --project-name ${PROJECT_NAME}_${DEV_GIT_BRANCH} -f docker-compose-main.yml up -d --build

start-dev: create-sample-env create-network start-services start-dev-application dev-available-at
	@echo "${GREEN}Started full development environment...${RESET}"

stop-dev: stop-dev-application stop-services
	@echo "${YELLOW}Stopping full development environment...${RESET}"

stop-prod-application:
	@echo "${YELLOW}Stopping the production instance of the application...${RESET}"
	docker compose --project-name ${PROJECT_NAME}_${PROD_GIT_BRANCH} -f docker-compose-prod.yml down

start-prod-application: stop-prod-application
	@echo "${YELLOW}Starting the production instance of the application...${RESET}"
	docker compose --project-name ${PROJECT_NAME}_${PROD_GIT_BRANCH} -f docker-compose-prod.yml up -d --build

clean-dev: stop-dev destroy-volume destroy-network
	@echo "${CYAN}Cleaning up Docker DEV containers, volumes, and networks...${RESET}"
	@echo "${GREEN}Cleanup completed.${RESET}"

clean-prod: stop-prod destroy-volume destroy-network
	@echo "${CYAN}Cleaning up Docker PROD containers, volumes, and networks...${RESET}"
	@echo "${GREEN}Cleanup completed.${RESET}"

start-prod: start-services create-network start-prod-application prod-available-at
	@echo "${GREEN}Started full production environment...${RESET}"

stop-prod: stop-prod-application stop-services
	@echo "${YELLOW}Stopping full production environment...${RESET}"

# --- Documentation ---
docs:
	@echo "${BLUE}Generating local documentation...${RESET}"
	pip3 install mkdocs-material --quiet
	python3 -m mkdocs serve -a localhost:8001

deploy-docs:
	@echo "${BLUE}Deploying documentation to GitHub Pages...${RESET}"
	pip3 install mkdocs-material --quiet
	python3 -m mkdocs gh-deploy --force

# --- Code Quality & Dependencies ---
pre-commit:
	@echo "${GREEN}Running pre-commit hooks...${RESET}"
	cd ${GIT_ROOT} && pre-commit run --all-files

sync-uv-dependencies:
	@echo "${CYAN}Synchronizing uv package dependencies...${RESET}"
	pip3 install uv --quiet
	cd ${GIT_ROOT}/bot_service/src/backend && uv pip compile requirements.txt -o requirements.in

install-dependencies:
	#@echo "${CYAN}Installing Python dependencies from requirements.txt...${RESET}"
	#pip3 install -r ${GIT_ROOT}/bot_service/src/backend/requirements.txt -U
	@echo "${CYAN}Installing Node.js dependencies for the frontend...${RESET}"
	cd ${GIT_ROOT}/bot_service/src/frontend && npm install --legacy-peer-deps || npm install --no-audit --no-fund

# --- Local Development & Testing ---
run-application-backend:
	@echo "${GREEN}Running the application backend locally...${RESET}"
	cd ${GIT_ROOT}/bot_service/src/backend && python3 main.py -e ./etc/.env

run-application-worker:
	@echo "${GREEN}Running the application worker locally...${RESET}"
	cd ${GIT_ROOT}/bot_service/src/backend && python3 worker.py -e ./etc/.env

run-application-frontend:
	@echo "${GREEN}Running the application frontend locally...${RESET}"
	cd ${GIT_ROOT}/bot_service/src/frontend && npm run dev

run-application: create-sample-env
	@echo "${GREEN}Starting all application components locally...${RESET}"
	@echo "${YELLOW}Note: This will start processes in the background. Use 'make stop-application' to stop them.${RESET}"

stop-application:
	@echo "${YELLOW}Stopping all application components...${RESET}"
	-pkill -f "python3 main.py"
	-pkill -f "python3 worker.py"
	-pkill -f "npm run dev"

tests:
	@echo "${GREEN}Running tests...${RESET}"
	pytest ${GIT_ROOT}/bot_service/src/backend/tests -v