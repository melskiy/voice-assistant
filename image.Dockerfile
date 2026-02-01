FROM python:3.12-slim

################################################################################
# Build instructions
################################################################################
RUN apt-get update && apt-get install -y --no-install-recommends \
	  curl jq build-essential gcc g++ git python3-pip openssh-client \
	&& pip install cython ujson \
    && apt-get purge -y build-essential \
    && apt-get clean -y \
    && apt-get autoremove -y \
    && apt-get autoclean -y \
	&& rm -rf /var/lib/{apt,dpkg,cache,log} /tmp/* ~/.cache \
    && rm -rf /usr/src/python /usr/share/doc /usr/share/man \
    && rm -f /var/cache/apt/archives/*.deb


# Create a non-root user for security
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Set the working directory to /app
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Change ownership to the app user
RUN chown -R appuser:appgroup /app

# Switch to the app user
USER appuser