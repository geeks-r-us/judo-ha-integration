# 🐳 Devcontainer Development Guide

This guide covers developing the Judo iSoft Home Assistant integration using VS Code devcontainers for instant development and testing.

## 🚀 Quick Start

### Prerequisites
- [VS Code](https://code.visualstudio.com/) with [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

### Launch Development Environment

1. **Clone and open in VS Code:**
```bash
git clone https://github.com/your-username/judo-ha-integration.git
cd judo-ha-integration
code .
```

2. **Open in devcontainer:**
   - VS Code will detect the devcontainer configuration
   - Click "Reopen in Container" when prompted
   - Or: Press `F1` → "Dev Containers: Reopen in Container"

3. **Wait for setup:**
   - The container will build and configure automatically
   - Dependencies will be installed
   - Home Assistant will start

4. **Access services:**
   - **Home Assistant:** http://localhost:8123
   - **Mock Device:** http://localhost:8080

## 🏗️ What's Included

### Services
- **Home Assistant:** Full HA instance for testing
- **Mock Judo Device:** Simulated device with realistic API responses
- **Python Debugger:** Remote debugging support

### Development Tools
- Python 3.11 with all dependencies
- VS Code extensions for HA development
- Pre-commit hooks
- Code formatting (Black, isort)
- Type checking (mypy)
- Testing framework (pytest)

### Pre-configured
- ✅ Integration linked to HA custom_components
- ✅ Development logger configuration
- ✅ Example automations and scripts
- ✅ Mock device for testing
- ✅ Debug configuration

## 🔧 Development Workflow

### 1. Initial Setup
After the devcontainer starts:

1. **Test the mock device:**
```bash
curl http://localhost:8080/api/status
```

2. **Configure the integration:**
   - Open Home Assistant: http://localhost:8123
   - Go to Settings → Devices & Services
   - Click "Add Integration"
   - Search for "Judo iSoft"
   - Configure with:
     - Host: `mock_device`
     - Port: `8080`

### 2. Making Changes

**Edit integration code:**
```bash
# Files are automatically synced
# Edit src/custom_components/judo_isoft/*.py
```

**Test your changes:**
```bash
# Run tests
pytest

# Format code
black src/ tests/
isort src/ tests/

# Type checking
mypy src/

# All checks
make check
```

**Restart Home Assistant:**
```bash
# In VS Code terminal
docker restart judo-isoft-homeassistant-dev
```

### 3. Testing with Mock Device

**View available endpoints:**
```bash
curl http://localhost:8080/
```

**Trigger test scenarios:**
```bash
# Trigger alarm
curl -X POST http://localhost:8080/api/control \
  -H 'Content-Type: application/json' \
  -d '{"command":"trigger_alarm"}'

# Set low salt level
curl -X POST http://localhost:8080/api/control \
  -H 'Content-Type: application/json' \
  -d '{"command":"set_salt_level", "value":15}'

# Start regeneration
curl -X POST http://localhost:8080/api/control \
  -H 'Content-Type: application/json' \
  -d '{"command":"start_regeneration"}'
```

**View current mock state:**
```bash
curl http://localhost:8080/api/control
```

## 🐛 Debugging

### Python Debugging
The devcontainer includes `debugpy` for remote debugging:

1. **Set breakpoints** in VS Code
2. **Attach debugger** to port 5678
3. **Debug configuration** is pre-configured in `.vscode/launch.json`

### Home Assistant Logs
```bash
# View HA logs
docker logs -f judo-isoft-homeassistant-dev

# View specific integration logs
docker exec judo-isoft-homeassistant-dev \
  tail -f /config/home-assistant.log | grep judo_isoft
```

### Integration Debugging
```bash
# Check if integration is loaded
curl http://localhost:8123/api/ -H "Authorization: Bearer YOUR_TOKEN"

# View entity states
curl http://localhost:8123/api/states -H "Authorization: Bearer YOUR_TOKEN"
```

## 📁 File Structure in Container

```
/workspaces/judo-ha-integration/     # Your source code (synced)
├── custom_components/judo_isoft/    # Integration source (HACS compliant)
└── tests/                          # Tests

/config/                             # Home Assistant config
├── configuration.yaml              # HA main config
├── custom_components/               # Custom integrations
│   └── judo_isoft/                 # ⬅️ Symlinked to your source
├── automations.yaml                # Example automations
└── *.log                          # Log files
```

## 🔄 Hot Reloading

Some changes require restarting Home Assistant:

**Automatic reload (no restart needed):**
- Template changes
- UI string changes
- Minor entity updates

**Manual restart required:**
- New entities
- Config flow changes  
- Major structural changes
- Manifest changes

**Restart Home Assistant:**
```bash
# Quick restart
docker restart judo-isoft-homeassistant-dev

# Or from HA UI: 
# Settings → System → Restart
```

## 🧪 Testing Scenarios

### Test Integration Loading
1. Check HA startup logs for errors
2. Verify integration appears in integrations list
3. Configure with mock device

### Test Sensor Updates
1. Watch sensor values in HA frontend
2. Trigger changes via mock device API
3. Verify entity states update

### Test Error Handling  
1. Stop mock device: `docker stop judo-isoft-mock-device`
2. Check entity availability
3. Restart: `docker start judo-isoft-mock-device`

### Test Automations
1. Trigger low salt level
2. Verify automation fires
3. Check notifications

## 🚨 Troubleshooting

### Container Won't Start
```bash
# Check Docker status
docker ps -a

# View build logs
docker logs judo-isoft-homeassistant-dev

# Rebuild container (if build fails)
# In VS Code: F1 → "Dev Containers: Rebuild Container"

# ✅ Fixed: Alpine Linux package manager compatibility
# Previous apt-get errors have been resolved
```

### Integration Not Loading
```bash
# Check custom_components link
ls -la /config/custom_components/

# Check integration syntax
python -m py_compile src/custom_components/judo_isoft/*.py

# View HA startup logs
docker logs judo-isoft-homeassistant-dev | grep -i judo
```

### Mock Device Issues
```bash
# Check mock device status  
curl http://localhost:8080/

# Restart mock device
docker restart judo-isoft-mock-device

# View mock device logs
docker logs judo-isoft-mock-device
```

### Development Tool Issues
```bash
# Reinstall dev dependencies
pip install -r requirements-dev.txt

# Reset pre-commit hooks
pre-commit uninstall
pre-commit install
```

## 🎯 Tips & Tricks

### Fast Development Cycle
1. Edit code in VS Code
2. Save file (auto-formatted)
3. Run `pytest tests/test_specific.py` for quick feedback
4. Restart HA only when needed

### Mock Device Scenarios
```bash
# Create realistic test scenario
curl -X POST http://localhost:8080/api/control -H 'Content-Type: application/json' -d '{"command":"set_salt_level", "value":18}'
curl -X POST http://localhost:8080/api/control -H 'Content-Type: application/json' -d '{"command":"trigger_maintenance"}'
curl -X POST http://localhost:8080/api/control -H 'Content-Type: application/json' -d '{"command":"start_regeneration"}' 
```

### VS Code Extensions
The devcontainer includes helpful extensions:
- **Home Assistant Config Helper** - YAML validation
- **Python** - Full Python support with debugging
- **GitHub Copilot** - AI code assistance

### Performance Monitoring
```bash
# Check integration performance
# In HA: Developer Tools → Statistics
# Look for judo_isoft entities update frequency
```

## 🌟 Next Steps

1. **Customize API integration** based on real device documentation
2. **Add more sensors** by updating `const.py`
3. **Enhance error handling** in `api.py`
4. **Write comprehensive tests** in `tests/`
5. **Submit pull request** when ready

The devcontainer provides a complete, isolated development environment that mirrors a real Home Assistant installation. Happy coding! 🚀