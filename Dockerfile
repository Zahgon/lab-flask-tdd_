##################################################
# Create production image
##################################################
# cSpell: disable
FROM quay.io/rofrano/python:3.12-slim

# Establish a working folder
WORKDIR /app

# Set up the Python production environment
COPY Pipfile Pipfile.lock ./
RUN python -m pip install --upgrade pip pipenv && \
    pipenv install --system --deploy

# Copy source files last because they change the most
COPY asgi.py .
COPY service ./service

# Switch to a non-root user and set file ownership
RUN useradd --uid 1001 flask && \
    chown -R flask:flask /app
USER flask

# Expose any ports the app is expecting in the environment
ENV PORT=8080
EXPOSE $PORT

ENTRYPOINT ["uvicorn"]
CMD ["--host=0.0.0.0", "--port=8080", "--log-level=info", "asgi:app"]
