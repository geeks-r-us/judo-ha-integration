FROM homeassistant/home-assistant:2024.2

# Set shell to bash for better compatibility
SHELL ["/bin/bash", "-c"]

# Install development tools (Alpine Linux)
RUN apk add --no-cache \
    git \
    curl \
    wget \
    vim \
    nano \
    build-base \
    python3-dev \
    bash \
    sudo \
    py3-pip

# Install Python development dependencies
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-homeassistant-custom-component \
    pytest-cov \
    black \
    isort \
    flake8 \
    mypy \
    pre-commit \
    debugpy

# Set up debugging
EXPOSE 5678

# Create custom components directory
RUN mkdir -p /config/custom_components

WORKDIR /workspaces/judo-ha-integration

# Default command
CMD ["python3", "-m", "homeassistant", "--config", "/config"]
