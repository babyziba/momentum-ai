# Use x86_64 Python 3.11 on Apple Silicon too
FROM --platform=linux/amd64 python:3.11-slim

# Prevent Python buffering stdout/stderr
ENV PYTHONUNBUFFERED=1

# Cloud Run sets PORT=8080 by default; default locally for testing
ENV PORT=8080

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the source code
COPY . .

# Make sure Python can find your code
ENV PYTHONPATH=/app:/app/src

# Expose the port that the app will run on
EXPOSE 8080

# Launch the FastAPI app
CMD ["python", "serve_agent.py"]
