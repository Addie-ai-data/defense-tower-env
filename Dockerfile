FROM python:3.12-slim

WORKDIR /app

# Use stable ABI fallback for PyO3/pydantic-core on Python 3.12+
ENV PYO3_USE_ABI3_FORWARD_COMPATIBILITY=1

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY src/ ./src/

# Set Python path so imports work
ENV PYTHONPATH=/app/src

# Default difficulty (override with -e TD_DIFFICULTY=hard)
ENV TD_DIFFICULTY=easy

EXPOSE 8000

CMD ["uvicorn", "envs.tower_defense.server.app:app", "--host", "0.0.0.0", "--port", "8000"]
