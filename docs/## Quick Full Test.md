## Quick Full Test

Run these in Git Bash:

cd /d/Proj/cl-ai
source .venv/Scripts/activate
export CLAI_DATA_DIR="$PWD/data/quick-test-$(date +%s)"

### 1. Automated tests

python -m pytest -q

Expected: 53 passed

### 2. Save, list, and show

cl-ai save 'az vm show --resource-group vnet-failsafe-dev-sea --name vm-failsafe-mgmt-dev --show-details --query "{Name:name,PowerState:powerState,PublicIP:publicIps,PrivateIP:privateIps}" -o table' --no-ai
cl-ai list
cl-ai show 1

### 3. Duplicate detection

cl-ai save "git status --short" --no-ai

Answer n.

### 4. Edit

cl-ai edit 1

Change the title or notes, then answer y.

### 5. Secret protection

cl-ai save "deploy --token fake-secret-value" --no-ai --yes

Expected: sensitive-data error.

### 6. Capture previous command

source <(cl-ai shell-init)
echo "capture test"
cl-ai save-last --no-ai --yes

### 7. Test longer capture phrase

git log -1 --oneline
cl-ai save the command --no-ai --yes

### 8. Test AI documentation

cl-ai save "terraform plan -out=tfplan" --yes

Requires working Qwen configuration.

### 9. Test chat

cl-ai

Ask:

Explain docker compose ps simply

Then type:

exit

### 10. Delete

cl-ai delete 1 --yes
cl-ai show 1

Expected: Command #1 was not found.

That tests every currently completed feature. Only AI documentation and chat require Qwen.


Expected:
cl-ai -get az vm that will show details of the deployed vm in azure
- It will show the command histoty lists



cl-ai --help "docker compose" give more options that I can use for more streamline
CL-AI | DOCKER COMPOSE COMMAND EXPLORER

Found useful Docker Compose commands:

[1] CHECK RUNNING SERVICES
    docker compose ps
    Shows the status of your containers.

[2] START SERVICES
    docker compose up -d
    Starts your services in the background.

[3] REBUILD AND START
    docker compose up -d --build
    Rebuilds images and starts services.

[4] VIEW LIVE LOGS
    docker compose logs -f --tail=100
    Shows the latest logs and follows new output.

[5] VIEW SPECIFIC SERVICE LOGS
    docker compose logs -f payment
    Shows live logs for the payment service.

[6] RESTART SERVICE
    docker compose restart payment
    Restarts the payment service.

[7] VALIDATE CONFIGURATION
    docker compose config -q
    Checks the Compose configuration.

[8] STOP SERVICES
    docker compose down
    Stops and removes Compose containers and networks.

[9] REMOVE CONTAINERS AND VOLUMES
    docker compose down -v
    WARNING: May delete stored volume data.

What would you like to do?

[1-9] Explain selected command
[S]   Save selected command to Vault
[M]   Show more commands
[Q]   Exit


cl-ai -save "terraform -chdir=terraform/environments/dev plan -out=tfplan"
It would give me

Field	                Saved information
Title	                Save Terraform Plan
Category	            Terraform / Planning
Command	                terraform -chdir=terraform/environments/dev plan -out=tfplan
Description	            Checks what Terraform will change and saves the plan to a file.
Purpose	                Review infrastructure changes before applying them.
Flags	                -chdir — Uses the dev folder.
                        -out — Saves the plan as tfplan.
Tags	                terraform, plan, dev, infrastructure
Risk	                Low for infrastructure changes. Does not apply changes, but the plan file may contain secrets.
Project	                failsafe-ecommerce
Directory	            /d/Proj/failsafe-ecommerce
Execution Status	    Not verified
Saved At	            Automatically recorded date and time


cl-ai -help "terraform -chdir=terraform/environments/dev plan " this is not working 