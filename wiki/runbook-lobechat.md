# Runbook: Lobe Chat (dev1)

## Start/Stop
- Start: `docker compose -f /home/mpegg-adm/source/TermiteTowers/docker/lobechat-dev1.yml up -d`
- Logs: `docker compose -f /home/mpegg-adm/source/TermiteTowers/docker/lobechat-dev1.yml logs -f`
- Stop: `docker compose -f /home/mpegg-adm/source/TermiteTowers/docker/lobechat-dev1.yml down`

## Ports
- Web: http://<host>:3100

## Env
- OPENAI_API_BASE_URL, OPENAI_API_KEY

## Troubleshooting
- If UI loads but requests fail, check that Ollama listens on 11434 and that host-gateway works on Linux.
