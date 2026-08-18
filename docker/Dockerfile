# RIFT — Reproducible evaluation environment
#
# Build args (recorded for traceability):
#   BUILD_DATE   — ISO-8601 date of image build
#   GIT_SHA      — git commit SHA at build time
#   HOST_KERNEL  — kernel version of the build host (uname -r output)
#   HOST_OS      — OS identifier of the build host
#
# Design:
#   - Python 3.11 slim base for minimal attack surface
#   - All pip deps installed from pinned requirements.txt
#   - iproute2 installed for tc/netem support in test mode
#   - Non-root user (rift) executes all tests
#   - Determinism: no --no-cache is needed because all deps are pinned
#     and the image layers are content-addressed by the pinned versions

FROM python:3.11-slim

# --------------------------------------------------------------------------
# Build-time traceability labels
# --------------------------------------------------------------------------

ARG BUILD_DATE="unknown"
ARG GIT_SHA="unknown"
ARG HOST_KERNEL="unknown"
ARG HOST_OS="unknown"

LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.revision="${GIT_SHA}"
LABEL rift.build.host_kernel="${HOST_KERNEL}"
LABEL rift.build.host_os="${HOST_OS}"
LABEL rift.python.version="3.11"
LABEL rift.purpose="reproducible-evaluation-testbed"

# --------------------------------------------------------------------------
# System packages
# --------------------------------------------------------------------------

RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
      # tc + ip for netem-based intervention mechanism
      iproute2 \
      # iptables for network partition interventions
      iptables \
      # git for recording HEAD SHA at test time
      git \
      # clean up layer
    && rm -rf /var/lib/apt/lists/*

# --------------------------------------------------------------------------
# Non-root user
# --------------------------------------------------------------------------

RUN groupadd --gid 1001 rift && \
    useradd --uid 1001 --gid rift --shell /bin/bash --create-home rift

# --------------------------------------------------------------------------
# Python dependencies (installed as root into the system site-packages
# before the user switch, so they are available read-only to the rift user)
# --------------------------------------------------------------------------

WORKDIR /opt/rift

COPY requirements.txt ./

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# --------------------------------------------------------------------------
# Copy project source
# --------------------------------------------------------------------------

COPY src/ ./src/
COPY tests/ ./tests/
COPY Makefile ./

# Create required artefact directories and make them writable by rift user
RUN mkdir -p artifacts/phase3 artifacts/coverage artifacts/logs && \
    chown -R rift:rift /opt/rift

# --------------------------------------------------------------------------
# Switch to non-root user
# --------------------------------------------------------------------------

USER rift

# --------------------------------------------------------------------------
# Default entrypoint: run the full test suite
# Overridable: docker run rift-eval make test-gate3a
# --------------------------------------------------------------------------

CMD ["python3.11", "-m", "pytest", "tests/", "--tb=short", "-v"]
