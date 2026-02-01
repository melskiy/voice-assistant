ARG IMAGE

################################################################################
# Base image: Voice Assistant Core
################################################################################
FROM $IMAGE AS image_with_app_code

# Switch to root to copy application files
USER root

# Copy the current directory contents into the container at /app
COPY . /app

# Change ownership to the app user
RUN chown -R appuser:appgroup /app

RUN pip install .

# Switch back to the app user
USER appuser

# Default command
CMD ["python", "-m", "src.main"]