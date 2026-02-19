#!/bin/bash

# Devcontainer setup script for Judo iSoft HA Integration

set -e

echo "🚀 Setting up Judo iSoft HA Integration development environment..."

# Create necessary directories
mkdir -p /config/custom_components
mkdir -p /config/themes
mkdir -p /config/blueprints
mkdir -p /config/www

# Install development dependencies in the workspace
if [ -d "/workspaces/judo-ha-integration" ]; then
    cd /workspaces/judo-ha-integration

    echo "📦 Installing Python dependencies..."
    pip3 install --upgrade pip || echo "⚠️ Warning: Could not upgrade pip"
    
    if [ -f "requirements-dev.txt" ]; then
        pip3 install -r requirements-dev.txt || echo "⚠️ Warning: Could not install all dev requirements"
    fi

    # Copy integration to custom_components
    echo "🔗 Linking integration to Home Assistant..."
    rm -rf /config/custom_components/judo_isoft
    if [ -d "custom_components/judo_isoft" ]; then
        ln -sf /workspaces/judo-ha-integration/custom_components/judo_isoft /config/custom_components/judo_isoft
    else
        echo "⚠️ Warning: Integration source not found at expected location"
    fi

    # Install pre-commit hooks if available
    echo "🪝 Installing pre-commit hooks..."
    if command -v pre-commit &> /dev/null; then
        pre-commit install || echo "⚠️ Warning: Could not install pre-commit hooks"
    fi
else
    echo "⚠️ Warning: Workspace directory not found"
fi

# Set proper permissions
chown -R root:root /config 2>/dev/null || true

# Create a simple test configuration file
echo "📝 Creating test configuration..."
cat > /config/.test_judo_config.yaml << EOF
# Test configuration for Judo iSoft integration
# Use this in automations.yaml or configuration.yaml
judo_isoft_test:
  host: "mock_device"  # Points to our mock device
  port: 8080
  scan_interval: 30
EOF

echo "✅ Development environment setup complete!"
echo "🌐 Home Assistant will be available at: http://localhost:8123"
echo "🔧 Mock Judo iSoft device available at: http://localhost:8080"
echo "🐛 Python debugger available on port: 5678"
echo ""
echo "📁 Integration source: /workspaces/judo-ha-integration/custom_components/judo_isoft"
echo "⚙️  HA config: /config"
echo "🔗 Integration linked to: /config/custom_components/judo_isoft"
echo ""
echo "To test your integration:"
echo "1. Wait for Home Assistant to start"
echo "2. Go to Settings → Devices & Services"
echo "3. Click Add Integration"
echo "4. Search for 'Judo iSoft'"
echo "5. Configure with host: mock_device, port: 8080"
