# Space Trace - VSCode DevContainer 

# Run with following commands:
# 1. Install the VSCode Remote-Containers extension
# 2. CMD + SHIFT + P
# 3. Remote-Containers: Rebuild and Reopen in Container

# [Choice] Python version (use -bullseye variants on local arm64/Apple Silicon): 3, 3.10, 3.9, 3.8, 3.7, 3.6, 3-bullseye, 3.10-bullseye, 3.9-bullseye, 3.8-bullseye, 3.7-bullseye, 3.6-bullseye, 3-buster, 3.10-buster, 3.9-buster, 3.8-buster, 3.7-buster, 3.6-buster
# ARG VARIANT="3.10-bullseye"
ARG VARIANT="3.10"
FROM mcr.microsoft.com/vscode/devcontainers/python:0-${VARIANT}

# install zbar tools
RUN sudo apt update -y
RUN sudo apt install -y zbar-tools

# install necessary dependencies
COPY requirements.txt /tmp/pip-tmp/
RUN pip3 --disable-pip-version-check --no-cache-dir install -r /tmp/pip-tmp/requirements.txt \
    && rm -rf /tmp/pip-tmp

# export flask app env variable
ENV FLASK_APP=space_trace