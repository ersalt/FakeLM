FROM python:3.11-slim

WORKDIR /app

# Copy dependency list and install
COPY fakellm/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY fakellm/ ./fakellm/
COPY main.py .

# Copy data files
COPY data/ ./data/

# Expose the configured port (default 8000)
EXPOSE 8000

# Run the server
CMD ["python", "main.py"]