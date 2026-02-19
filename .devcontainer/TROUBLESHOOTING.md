# 🐳 Devcontainer Troubleshooting

## Fixed Issues

### ✅ Alpine Linux Package Manager
**Problem:** `apt-get` commands failed with exit code 127  
**Solution:** Updated Dockerfile to use Alpine Linux's `apk` package manager instead of `apt-get`

### ✅ Improved Error Handling
**Problem:** Setup scripts could fail silently  
**Solution:** Added error handling and fallbacks in setup scripts

### ✅ Port Forwarding
**Problem:** Mock device port not exposed  
**Solution:** Added port 8080 forwarding for mock Judo device

## Quick Fixes

### Cannot Connect to Home Assistant
```bash
# Check container status
docker ps

# View logs
docker logs judo-isoft-homeassistant-dev

# Restart container
docker restart judo-isoft-homeassistant-dev
```

### Build Failures
```bash
# Clean and rebuild
docker system prune -f
# Then: F1 → "Dev Containers: Rebuild Container" in VS Code
```

### Integration Not Loading
```bash
# Check if integration is linked
docker exec judo-isoft-homeassistant-dev ls -la /config/custom_components/

# Manually create link if needed
docker exec judo-isoft-homeassistant-dev \
  ln -sf /workspaces/judo-ha-integration/src/custom_components/judo_isoft \
         /config/custom_components/judo_isoft
```

### Python Dependencies Issues
```bash
# Reinstall in container
docker exec -it judo-isoft-homeassistant-dev bash
cd /workspaces/judo-ha-integration
pip3 install -r requirements-dev.txt
```

### Mock Device Not Reachable
```bash
# Check mock device container
docker ps | grep mock

# Restart mock device
docker restart judo-isoft-mock-device

# View mock device logs
docker logs judo-isoft-mock-device
```

## Environment Variables

- `PYTHONPATH`: Set to include integration source
- `TZ`: Set to UTC
- Container user: `root` (for HA compatibility)

## Useful Commands

```bash
# View all containers
docker ps -a

# Follow HA logs
docker logs -f judo-isoft-homeassistant-dev

# Enter HA container
docker exec -it judo-isoft-homeassistant-dev bash

# Enter mock device container  
docker exec -it judo-isoft-mock-device sh

# Restart all services
docker compose -f .devcontainer/docker-compose.yml restart
```