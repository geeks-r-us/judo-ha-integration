#!/bin/bash

# Devcontainer start script for Judo iSoft HA Integration

echo "🔄 Starting Judo iSoft HA Integration development environment..."

# Ensure integration is properly linked
if [ ! -L "/config/custom_components/judo_isoft" ] && [ -d "/workspaces/judo-ha-integration/src/custom_components/judo_isoft" ]; then
    echo "🔗 Re-linking integration..."
    rm -rf /config/custom_components/judo_isoft
    ln -sf /workspaces/judo-ha-integration/src/custom_components/judo_isoft /config/custom_components/judo_isoft
fi

# Set working directory if it exists
if [ -d "/workspaces/judo-ha-integration" ]; then
    cd /workspaces/judo-ha-integration
fi

# Update PYTHONPATH to include our source
export PYTHONPATH="/workspaces/judo-ha-integration/src:/config/custom_components:$PYTHONPATH"

echo "🐍 Python path: $PYTHONPATH"
echo "📁 Working directory: $(pwd)"
echo "🏠 Starting Home Assistant in development mode..."
