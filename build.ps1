param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

# Global variables

# Determine git root directory, with PSScriptRoot as fallback
try {
    $GIT_ROOT = & git rev-parse --show-toplevel 2>$null
    if (-not $GIT_ROOT) {
        $GIT_ROOT = $PSScriptRoot
    }
} catch {
    $GIT_ROOT = $PSScriptRoot
}
$DEV_GIT_BRANCH = "main"
$PROD_GIT_BRANCH = "prod"
$PROJECT_NAME = (Split-Path $GIT_ROOT -Leaf).ToLower()

# Color definitions for console output
$Colors = @{
    Green  = "Green"
    Yellow = "Yellow"
    Blue   = "Blue"
    Cyan   = "Cyan"
    Red    = "Red"
}

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    try {
        # Ensure the message is treated as a literal string
        $SafeMessage = [string]$Message
        Write-Host $SafeMessage -ForegroundColor $Color
    }
    catch {
        # Fallback to plain Write-Host without color if there's an issue
        Write-Host $Message
        Write-Host "DEBUG: Error in Write-ColorOutput: $($_.Exception.Message)" -ForegroundColor Red
    }
}

function Show-Help {
    Write-ColorOutput "Available commands:" $Colors.Yellow
    Write-ColorOutput ""
    Write-ColorOutput "Documentation:" $Colors.Cyan
    Write-ColorOutput "  docs                      : Generate local documentation in the /docs folder using MkDocs." $Colors.Green
    Write-ColorOutput "  deploy-docs               : Deploy the generated documentation to GitHub Pages." $Colors.Green
    Write-ColorOutput ""
    Write-ColorOutput "Code Quality:" $Colors.Cyan
    Write-ColorOutput "  pre-commit                : Install and run pre-commit hooks for code quality checks." $Colors.Green
    Write-ColorOutput "  tests                     : Run tests using pytest." $Colors.Green
    Write-ColorOutput ""
    Write-ColorOutput "Database Migrations (Alembic):" $Colors.Cyan
    Write-ColorOutput "  init-alembic              : Initialize Alembic for database migrations." $Colors.Green
    Write-ColorOutput "  add-alembic-revision      : Auto-generate an Alembic revision for database migrations." $Colors.Green
    Write-ColorOutput "  upgrade-alembic-revision  : Upgrade the database schema to the latest Alembic revision." $Colors.Green
    Write-ColorOutput "  downgrade-alembic-revision: Downgrade the database schema by one revision." $Colors.Green
    Write-ColorOutput "  show-alembic-history      : Show the Alembic migration history." $Colors.Green
    Write-ColorOutput "  show-alembic-current      : Show the current Alembic revision." $Colors.Green
    Write-ColorOutput "  stamp-alembic-revision    : Stamp the database with the latest Alembic revision." $Colors.Green
    Write-ColorOutput ""
    Write-ColorOutput "Docker Infrastructure:" $Colors.Cyan
    Write-ColorOutput "  create-volume             : Create the required Docker volumes." $Colors.Green
    Write-ColorOutput "  destroy-volume            : Remove the Docker volumes." $Colors.Green
    Write-ColorOutput "  create-network            : Create the required Docker networks." $Colors.Green
    Write-ColorOutput "  destroy-network           : Remove the Docker networks." $Colors.Green
    Write-ColorOutput "  clean-docker-cache        : Prune Docker build cache and builder cache." $Colors.Green
    Write-ColorOutput ""
    Write-ColorOutput "Docker Services:" $Colors.Cyan
    Write-ColorOutput "  start-services            : Stop then start all services with rebuild in detached mode." $Colors.Green
    Write-ColorOutput "  stop-services             : Stop all running Docker services as defined in docker-compose-services.yml." $Colors.Green
    Write-ColorOutput "  list-services             : List all Docker services and their status." $Colors.Green
    Write-ColorOutput "  list-volumes              : List all Docker volumes." $Colors.Green
    Write-ColorOutput ""
    Write-ColorOutput "Development Environment:" $Colors.Cyan
    Write-ColorOutput "  start-dev                 : Start full development environment (services + application)." $Colors.Green
    Write-ColorOutput "  stop-dev                  : Stop full development environment (application + services)." $Colors.Green
    Write-ColorOutput "  start-dev-application     : Start the development instance of the application with rebuild." $Colors.Green
    Write-ColorOutput "  stop-dev-application      : Shut down the development instance of the application." $Colors.Green
    Write-ColorOutput "  list-dev-containers       : List all development Docker containers." $Colors.Green
    Write-ColorOutput "  clean-dev                 : Clean up development containers, volumes, and networks." $Colors.Green
    Write-ColorOutput "  dev-available-at          : Show all available development service URLs." $Colors.Green
    Write-ColorOutput ""
    Write-ColorOutput "Production Environment:" $Colors.Cyan
    Write-ColorOutput "  start-prod                : Start full production environment (services + application)." $Colors.Green
    Write-ColorOutput "  stop-prod                 : Stop full production environment (application + services)." $Colors.Green
    Write-ColorOutput "  start-prod-application    : Start the production instance of the application with rebuild." $Colors.Green
    Write-ColorOutput "  stop-prod-application     : Stop the production instance of the application." $Colors.Green
    Write-ColorOutput "  list-prod-containers      : List all production Docker containers." $Colors.Green
    Write-ColorOutput "  clean-prod                : Clean up production containers, volumes, and networks." $Colors.Green
    Write-ColorOutput "  prod-available-at         : Show all available production service URLs." $Colors.Green
    Write-ColorOutput ""
    Write-ColorOutput "Dependencies:" $Colors.Cyan
    Write-ColorOutput "  sync-uv-dependencies      : Synchronize the uv package dependencies by updating requirements." $Colors.Green
    Write-ColorOutput "  install-dependencies      : Install Python dependencies from requirements.txt for local run." $Colors.Green
    Write-ColorOutput ""
    Write-ColorOutput "Local Development:" $Colors.Cyan
    Write-ColorOutput "  run-application           : Start all application components locally in background." $Colors.Green
    Write-ColorOutput "  stop-application          : Stop all locally running application components." $Colors.Green
    Write-ColorOutput "  run-application-backend   : Run the application backend locally." $Colors.Green
    Write-ColorOutput "  run-application-worker    : Run the application worker locally." $Colors.Green
    Write-ColorOutput "  run-application-frontend  : Run the application frontend locally." $Colors.Green
    Write-ColorOutput ""
    Write-ColorOutput "Utilities:" $Colors.Cyan
    Write-ColorOutput "  create-sample-env         : Create sample .env files for backend, frontend & services." $Colors.Green
}

# --- Alembic Database Migrations ---
function Initialize-Alembic {
    Write-ColorOutput "Initializing Alembic for database migrations..." $Colors.Blue
    Set-Location "$GIT_ROOT\bot_service\src\backend"
    & alembic init alembic
}

function Add-AlembicRevision {
    Write-ColorOutput "Auto-generating an Alembic revision for database migrations..." $Colors.Blue
    $message = Read-Host "Enter alembic commit message"
    Write-ColorOutput "Your alembic commit message is: $message" $Colors.Cyan
    Set-Location "$GIT_ROOT\bot_service\src\backend"
    & alembic revision --autogenerate -m $message
}

function Update-AlembicRevision {
    Write-ColorOutput "Upgrading the database schema to the latest Alembic revision..." $Colors.Blue
    Set-Location "$GIT_ROOT\bot_service\src\backend"
    & alembic upgrade head
}

function Downgrade-AlembicRevision {
    Write-ColorOutput "Downgrading the database schema by one revision..." $Colors.Blue
    Set-Location "$GIT_ROOT\bot_service\src\backend"
    & alembic downgrade -1
}

function Show-AlembicHistory {
    Write-ColorOutput "Showing the Alembic migration history..." $Colors.Blue
    Set-Location "$GIT_ROOT\bot_service\src\backend"
    & alembic history --verbose
}

function Show-AlembicCurrent {
    Write-ColorOutput "Showing the current Alembic revision..." $Colors.Blue
    Set-Location "$GIT_ROOT\bot_service\src\backend"
    & alembic current
}

function Set-AlembicRevision {
    Write-ColorOutput "Stamping the database with the latest Alembic revision..." $Colors.Blue
    Set-Location "$GIT_ROOT\bot_service\src\backend"
    & alembic stamp head
}

# --- Docker Management ---
function New-DockerVolume {
    Write-ColorOutput "Creating Docker volumes..." $Colors.Cyan
    try { & docker volume create postgres_data } catch { }
    try { & docker volume create pgadmin_data } catch { }
    try { & docker volume create redis_data } catch { }
}

function New-DockerNetwork {
    Write-ColorOutput "Creating Docker networks..." $Colors.Cyan
    try { & docker network create -d bridge shared_network } catch { }
}

function Remove-DockerVolume {
    Write-ColorOutput "Destroying Docker volumes..." $Colors.Cyan
    try { & docker volume rm postgres_data } catch { }
    try { & docker volume rm pgadmin_data } catch { }
    try { & docker volume rm redis_data } catch { }
}

function Remove-DockerNetwork {
    Write-ColorOutput "Destroying Docker networks..." $Colors.Cyan
    try { & docker network rm shared_network } catch { }
}

function Clear-DockerCache {
    Write-ColorOutput "Pruning Docker build cache and builder cache..." $Colors.Cyan
    & docker buildx prune -a -f
    & docker builder prune -a -f
}

function Get-ServicesList {
    Write-ColorOutput "Listing Docker services..." $Colors.Cyan
    & docker compose --project-name $PROJECT_NAME -f docker-compose-services.yml ps --format 'table {{.Names}}\t\t{{.Ports}}' | Where-Object { $_ -match "NAMES|0\.0\.0\.0" } | ForEach-Object { $_ -replace "0\.0\.0\.0:", "" -replace "->[^,]*", "" -replace ",.*", "" -replace "<no value>", "NAMES" }
}

function Get-VolumesList {
    Write-ColorOutput "Listing Docker volumes..." $Colors.Cyan
    & docker volume ls
}

function Get-DevContainersList {
    Write-ColorOutput "Listing Docker development containers..." $Colors.Cyan
    & docker compose --project-name "${PROJECT_NAME}_${DEV_GIT_BRANCH}" -f docker-compose-main.yml ps --format 'table {{.Names}}\t\t{{.Ports}}' | Where-Object { $_ -match "NAMES|0\.0\.0\.0" } | ForEach-Object { $_ -replace "0\.0\.0\.0:", "" -replace "->[^,]*", "" -replace ",.*", "" -replace "<no value>", "NAMES" }
}

function Get-ProdContainersList {
    Write-ColorOutput "Listing Docker production containers..." $Colors.Cyan
    & docker compose --project-name "${PROJECT_NAME}_${PROD_GIT_BRANCH}" -f docker-compose-prod.yml ps --format 'table {{.Names}}\t\t{{.Ports}}' | Where-Object { $_ -match "NAMES|0\.0\.0\.0" } | ForEach-Object { $_ -replace "0\.0\.0\.0:", "" -replace "->[^,]*", "" -replace ",.*", "" -replace "<no value>", "NAMES" }
}

function Stop-Services {
    Write-ColorOutput "Stopping Docker services..." $Colors.Cyan
    & docker compose --project-name $PROJECT_NAME -f docker-compose-services.yml down
}

function Start-Services {
    Stop-Services
    New-DockerVolume
    Write-ColorOutput "Starting Docker services..." $Colors.Cyan
    & docker compose --project-name $PROJECT_NAME -f docker-compose-services.yml up -d --build
}

function Stop-DevApplication {
    Write-ColorOutput "Shutting down the development instance of the application..." $Colors.Yellow
    & docker compose --project-name "${PROJECT_NAME}_${DEV_GIT_BRANCH}" -f docker-compose-main.yml down
}

function Start-DevApplication {
    Stop-DevApplication
    Write-ColorOutput "Starting the development instance of the application..." $Colors.Yellow
    & docker compose --project-name "${PROJECT_NAME}_${DEV_GIT_BRANCH}" -f docker-compose-main.yml up -d --build
}

function Start-Dev {
    New-SampleEnv
    New-DockerNetwork
    Start-Services
    Start-DevApplication
    Show-DevAvailableAt
    Write-ColorOutput "Started full development environment..." $Colors.Green
}

function Show-DevAvailableAt {
    Write-ColorOutput "+---------------------------------------------------------------+" $Colors.Cyan
    Write-ColorOutput "|                    DEVELOPMENT ENVIRONMENT                    |" $Colors.Cyan
    Write-ColorOutput "+---------------------------------------------------------------+" $Colors.Cyan
    Write-ColorOutput ""
    Write-ColorOutput "Application Services:" $Colors.Cyan
    Get-ServicesList
    Write-ColorOutput ""
    Write-ColorOutput "Development Containers:" $Colors.Cyan
    Get-DevContainersList
    Write-ColorOutput ""
    Write-ColorOutput "---------------------------------------------------------------" $Colors.Cyan
    Write-ColorOutput "Admin Credentials:" $Colors.Yellow
    Write-ColorOutput "  Email:    CUSTOM_OAUTH_BOOTSTRAP_ADMIN_EMAIL (from .env)" $Colors.Green
    Write-ColorOutput "  Password: CUSTOM_OAUTH_BOOTSTRAP_ADMIN_PASSWORD (from .env)" $Colors.Green
    Write-ColorOutput "  Config:   ${GIT_ROOT}\bot_service\src\backend\etc\.env" $Colors.Blue
    Write-ColorOutput ""
    Write-ColorOutput "Note: Ports and host settings may vary based on .env configuration" $Colors.Yellow
    Write-ColorOutput "---------------------------------------------------------------" $Colors.Cyan
}

function Show-ProdAvailableAt {
    Write-ColorOutput "+---------------------------------------------------------------+" $Colors.Cyan
    Write-ColorOutput "|                     PRODUCTION ENVIRONMENT                    |" $Colors.Cyan
    Write-ColorOutput "+---------------------------------------------------------------+" $Colors.Cyan
    Write-ColorOutput ""
    Write-ColorOutput "Application Services:" $Colors.Cyan
    Get-ServicesList
    Write-ColorOutput ""
    Write-ColorOutput "Production Containers:" $Colors.Cyan
    Get-ProdContainersList
    Write-ColorOutput ""
    Write-ColorOutput "---------------------------------------------------------------" $Colors.Cyan
    Write-ColorOutput "Admin Credentials:" $Colors.Yellow
    Write-ColorOutput "  Email:    CUSTOM_OAUTH_BOOTSTRAP_ADMIN_EMAIL (from .env)" $Colors.Green
    Write-ColorOutput "  Password: CUSTOM_OAUTH_BOOTSTRAP_ADMIN_PASSWORD (from .env)" $Colors.Green
    Write-ColorOutput "  Config:   ${GIT_ROOT}\bot_service\src\backend\etc\.env" $Colors.Blue
    Write-ColorOutput ""
    Write-ColorOutput "Note: Ports and host settings may vary based on .env configuration" $Colors.Yellow
    Write-ColorOutput "---------------------------------------------------------------" $Colors.Cyan
}

function Show-AvailableAt {
    Show-DevAvailableAt
}

function Stop-Dev {
    Stop-DevApplication
    Stop-Services
    Write-ColorOutput "Stopping full development environment..." $Colors.Yellow
}

function Stop-ProdApplication {
    Write-ColorOutput "Stopping the production instance of the application..." $Colors.Yellow
    & docker compose --project-name "${PROJECT_NAME}_${PROD_GIT_BRANCH}" -f docker-compose-prod.yml down
}

function Start-ProdApplication {
    Stop-ProdApplication
    Write-ColorOutput "Starting the production instance of the application..." $Colors.Yellow
    & docker compose --project-name "${PROJECT_NAME}_${PROD_GIT_BRANCH}" -f docker-compose-prod.yml up -d --build
}

function Start-Prod {
    Start-Services
    Start-ProdApplication
    Show-ProdAvailableAt
    Write-ColorOutput "Started full production environment..." $Colors.Green
}

function Stop-Prod {
    Stop-ProdApplication
    Stop-Services
    Write-ColorOutput "Stopping full production environment..." $Colors.Yellow
}

function Clear-Dev {
    Stop-Dev
    Remove-DockerVolume
    Remove-DockerNetwork
    Write-ColorOutput "Cleaning up Docker DEV containers, volumes, and networks..." $Colors.Cyan
    Write-ColorOutput "Cleanup completed." $Colors.Green
}

function Clear-Prod {
    Stop-Prod
    Remove-DockerVolume
    Remove-DockerNetwork
    Write-ColorOutput "Cleaning up Docker PROD containers, volumes, and networks..." $Colors.Cyan
    Write-ColorOutput "Cleanup completed." $Colors.Green
}

# --- Documentation ---
function Start-Docs {
    Write-ColorOutput "Generating local documentation..." $Colors.Blue
    & pip3 install mkdocs-material --quiet
    & python3 -m mkdocs serve -a localhost:8001
}

function Deploy-Docs {
    Write-ColorOutput "Deploying documentation to GitHub Pages..." $Colors.Blue
    & pip3 install mkdocs-material --quiet
    & python3 -m mkdocs gh-deploy --force
}

# --- Code Quality & Dependencies ---
function Start-PreCommit {
    Write-ColorOutput "Running pre-commit hooks..." $Colors.Green
    Set-Location $GIT_ROOT
    & pre-commit run --all-files
}

function Sync-UvDependencies {
    Write-ColorOutput "Synchronizing uv package dependencies..." $Colors.Cyan
    & pip3 install uv --quiet
    Set-Location "$GIT_ROOT\bot_service\src\backend"
    & uv pip compile requirements.txt -o requirements.in
}

function Install-Dependencies {
    Write-ColorOutput "Installing Python dependencies from requirements.txt..." $Colors.Cyan
    & pip3 install -r "$GIT_ROOT\bot_service\src\backend\requirements.txt" -U
    Write-ColorOutput "Installing Node.js dependencies for the frontend..." $Colors.Cyan
    Set-Location "$GIT_ROOT\bot_service\src\frontend"
    & npm install --legacy-peer-deps
}

# --- Local Development & Testing ---
function Start-ApplicationBackend {
    Write-ColorOutput "Running the application backend locally..." $Colors.Green
    Set-Location "$GIT_ROOT\bot_service\src\backend"
    & python3 main.py -e .\etc\.env
}

function Start-ApplicationWorker {
    Write-ColorOutput "Running the application worker locally..." $Colors.Green
    Set-Location "$GIT_ROOT\bot_service\src\backend"
    & python3 worker.py -e .\etc\.env
}

function Start-ApplicationFrontend {
    Write-ColorOutput "Running the application frontend locally..." $Colors.Green
    Set-Location "$GIT_ROOT\bot_service\src\frontend"
    & npm run dev
}

function Start-Tests {
    Write-ColorOutput "Running tests..." $Colors.Green
    & pytest "$GIT_ROOT\bot_service\src\backend\tests" -v
}

function Start-Application {
    New-SampleEnv
    Write-ColorOutput "Starting all application components locally..." $Colors.Green
    Write-ColorOutput "Note: This will start processes in the background. Use 'Stop-Application' to stop them." $Colors.Yellow

    # Start backend in background
    Start-Job -Name "BackendJob" -ScriptBlock {
        param($gitRoot, $colors)
        Set-Location "$gitRoot\bot_service\src\backend"
        & python3 main.py -e .\etc\.env
    } -ArgumentList $GIT_ROOT, $Colors
    
    # Start worker in background
    Start-Job -Name "WorkerJob" -ScriptBlock {
        param($gitRoot, $colors)
        Set-Location "$gitRoot\bot_service\src\backend"
        & python3 worker.py -e .\etc\.env
    } -ArgumentList $GIT_ROOT, $Colors
    
    # Start frontend in background
    Start-Job -Name "FrontendJob" -ScriptBlock {
        param($gitRoot, $colors)
        Set-Location "$gitRoot\bot_service\src\frontend"
        & npm run dev
    } -ArgumentList $GIT_ROOT, $Colors
    
    Write-ColorOutput "All application components are now running locally..." $Colors.Green
    Write-ColorOutput "Use 'Get-Job' to check status and 'Stop-Application' to stop all components." $Colors.Cyan
}

function Stop-Application {
    Write-ColorOutput "Stopping all application components..." $Colors.Yellow
    
    # Stop PowerShell jobs
    Get-Job -Name "BackendJob" -ErrorAction SilentlyContinue | Stop-Job
    Get-Job -Name "WorkerJob" -ErrorAction SilentlyContinue | Stop-Job
    Get-Job -Name "FrontendJob" -ErrorAction SilentlyContinue | Stop-Job
    
    # Remove completed jobs
    Get-Job -State Completed | Remove-Job
    
    # Kill processes by name pattern (Windows equivalent of pkill)
    try {
        # Kill Python processes running main.py
        Get-Process | Where-Object { $_.ProcessName -like "*python*" } | Where-Object { 
            try { $_.MainModule.FileName -like "*python*" -and (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine -like "*main.py*" } catch { $false }
        } | Stop-Process -Force -ErrorAction SilentlyContinue
        
        # Kill Python processes running worker.py
        Get-Process | Where-Object { $_.ProcessName -like "*python*" } | Where-Object { 
            try { $_.MainModule.FileName -like "*python*" -and (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine -like "*worker.py*" } catch { $false }
        } | Stop-Process -Force -ErrorAction SilentlyContinue
        
        # Kill npm processes running dev
        Get-Process | Where-Object { $_.ProcessName -like "*node*" } | Where-Object { 
            try { (Get-WmiObject Win32_Process -Filter "ProcessId = $($_.Id)").CommandLine -like "*npm*run*dev*" } catch { $false }
        } | Stop-Process -Force -ErrorAction SilentlyContinue
    } catch {
        Write-ColorOutput "Some processes may still be running. Check manually if needed." $Colors.Yellow
    }
    
    Write-ColorOutput "Application components stopped." $Colors.Green
}

# --- Miscellaneous ---
function New-SampleEnv {
    $response = Read-Host "Do you want to create sample .env file for the frontend, backend & common services? (y/n)"
    if ($response -eq "y") {
        Write-ColorOutput "Creating sample .env files for backend, frontend & common services ..." $Colors.Cyan
        
        if (-not (Test-Path "$GIT_ROOT\bot_service\src\frontend\.env")) {
            Copy-Item "$GIT_ROOT\bot_service\src\frontend\.env_sample" "$GIT_ROOT\bot_service\src\frontend\.env"
        }
        
        if (-not (Test-Path "$GIT_ROOT\bot_service\src\backend\etc\.env")) {
            Copy-Item "$GIT_ROOT\bot_service\src\backend\etc\.env_sample" "$GIT_ROOT\bot_service\src\backend\etc\.env"
        }
        
        if (-not (Test-Path "$GIT_ROOT\.env")) {
            Copy-Item "$GIT_ROOT\.env_services_sample" "$GIT_ROOT\.env"
        }
        
        Write-ColorOutput "Sample .env files created successfully!" $Colors.Green
        Write-ColorOutput "You can edit $GIT_ROOT\bot_service\src\backend\etc\.env to configure your environment." $Colors.Cyan
        Write-ColorOutput "You can edit $GIT_ROOT\bot_service\src\frontend\.env to configure your environment." $Colors.Cyan
        Write-ColorOutput "You can edit $GIT_ROOT\.env to configure your environment." $Colors.Cyan
    } else {
        Write-ColorOutput "Skipping .env file creation." $Colors.Yellow
    }
}

# Main command router
try {
    switch ($Command.ToLower()) {
        "help" { Show-Help }
        "docs" { Start-Docs }
        "deploy-docs" { Deploy-Docs }
        "pre-commit" { Start-PreCommit }
        "init-alembic" { Initialize-Alembic }
        "add-alembic-revision" { Add-AlembicRevision }
        "upgrade-alembic-revision" { Update-AlembicRevision }
        "downgrade-alembic-revision" { Downgrade-AlembicRevision }
        "show-alembic-history" { Show-AlembicHistory }
        "show-alembic-current" { Show-AlembicCurrent }
        "stamp-alembic-revision" { Set-AlembicRevision }
        "create-volume" { New-DockerVolume }
        "destroy-volume" { Remove-DockerVolume }
        "create-network" { New-DockerNetwork }
        "destroy-network" { Remove-DockerNetwork }
        "clean-docker-cache" { Clear-DockerCache }
        "list-services" { Get-ServicesList }
        "list-volumes" { Get-VolumesList }
        "list-dev-containers" { Get-DevContainersList }
        "list-prod-containers" { Get-ProdContainersList }
        "stop-services" { Stop-Services }
        "start-services" { Start-Services }
        "stop-dev-application" { Stop-DevApplication }
        "start-dev-application" { Start-DevApplication }
        "start-dev" { Start-Dev }
        "stop-dev" { Stop-Dev }
        "clean-dev" { Clear-Dev }
        "stop-prod-application" { Stop-ProdApplication }
        "start-prod-application" { Start-ProdApplication }
        "start-prod" { Start-Prod }
        "stop-prod" { Stop-Prod }
        "clean-prod" { Clear-Prod }
        "sync-uv-dependencies" { Sync-UvDependencies }
        "install-dependencies" { Install-Dependencies }
        "tests" { Start-Tests }
        "run-application-backend" { Start-ApplicationBackend }
        "run-application-worker" { Start-ApplicationWorker }
        "run-application-frontend" { Start-ApplicationFrontend }
        "run-application" { Start-Application }
        "stop-application" { Stop-Application }
        "available-at" { Show-AvailableAt }
        "dev-available-at" { Show-DevAvailableAt }
        "prod-available-at" { Show-ProdAvailableAt }
        "create-sample-env" { New-SampleEnv }
        default { 
            Write-ColorOutput "Unknown command: $Command" $Colors.Red
            Write-ColorOutput ""
            Show-Help 
        }
    }
} catch {
    Write-ColorOutput "Error executing command: $_" $Colors.Red
    exit 1
}
