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