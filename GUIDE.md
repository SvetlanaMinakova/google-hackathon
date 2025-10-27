# How to Start

## Steps

- Install uv
- Install make
- Install google cloud cli
- Run `gcloud init --no-launch-browser`
- Copy the the provided link and follow the instructions
- Run `uvx agent-starter-pack enhance --adk -d agent_engine`
- Select defaults, the only exception is region - use eu-west4
- Run `gcloud auth application-default login --no-launch-browser` and follow instructions
- The right project should be set, verify using `gcloud config get-value project`
- Create `.env` file `echo 'GOOGLE_API_KEY="YOUR_API_KEY"' > .env`
- Run `uv sync`

## Deploying to Code Run (recommended)

- Create the agent
- Create .env file and run `source .env`
- .env file content:

```
export GOOGLE_GENAI_USE_VERTEXAI=1
export GOOGLE_CLOUD_PROJECT=qwiklabs-gcp-04-031dca97b094
export GOOGLE_CLOUD_LOCATION=europe-west4
export AGENT_PATH="./test_agent"
export SERVICE_NAME="test-agent-service"
export APP_NAME="test-agent-app"
```

- Run 
```bash
uv run adk deploy cloud_run \
    --project=$GOOGLE_CLOUD_PROJECT \
    --region=$GOOGLE_CLOUD_LOCATION \
    --service_name=$SERVICE_NAME \
    --app_name=$APP_NAME \
    --with_ui \
    $AGENT_PATH
```
