FROM ghcr.io/home-assistant/home-assistant:stable

# Set shell to bash for better compatibility
SHELL ["/bin/bash", "-c"]

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=1000

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

# Create a non-root development user matching host UID/GID.
RUN addgroup -g "${USER_GID}" "${USERNAME}" && \
    adduser -D -u "${USER_UID}" -G "${USERNAME}" "${USERNAME}" && \
    echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Dev/test tooling lives in its own venv. Installing pytest-homeassistant-custom-component
# into the system environment would replace the image's Home Assistant with the
# version that plugin pins and break its bundled dependencies.
RUN python3 -m venv /opt/devenv && \
    /opt/devenv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/devenv/bin/pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-homeassistant-custom-component \
    pytest-cov \
    black \
    isort \
    flake8 \
    mypy \
    pre-commit \
    debugpy && \
    chown -R "${USER_UID}:${USER_GID}" /opt/devenv

# Home Assistant installs integration requirements at runtime as the non-root user
RUN chown -R "${USER_UID}:${USER_GID}" /usr/local/lib/python3*/site-packages /usr/local/bin

ENV PATH="${PATH}:/opt/devenv/bin"

# Set up debugging
EXPOSE 5678

# Create custom components directory
RUN mkdir -p /config/custom_components /workspaces/judo-ha-integration && \
    chown -R "${USER_UID}:${USER_GID}" /config /workspaces

WORKDIR /workspaces/judo-ha-integration

USER ${USERNAME}

# Default command
CMD ["python3", "-m", "homeassistant", "--config", "/config"]
