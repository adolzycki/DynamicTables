FROM python:3.12

# Set environment varibles
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  PIP_NO_CACHE_DIR=1 \
  PIP_DISABLE_PIP_VERSION_CHECK=1 \
  PIP_DEFAULT_TIMEOUT=100 \
  PIPENV_HIDE_EMOJIS=1 \
  PIPENV_COLORBLIND=1 \
  PIPENV_NOSPIN=1

# Set work directory
WORKDIR /app

# Copy project
COPY . /app

# Install dependencies
RUN apt-get update \
    # Application dependencies
    && pip install pipenv \
    && pipenv sync --system --dev
