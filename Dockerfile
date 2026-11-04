# Fraud Detection System dashboard. The LLM runs in a separate Ollama container
# (see docker-compose.yml); without it, explanations fall back to templates.
FROM python:3.13-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ src/
COPY data/customers.csv data/transactions.csv data/
COPY app.py .

# Run as an unprivileged user.
RUN useradd --create-home appuser && mkdir -p results && chown appuser results
USER appuser

EXPOSE 8501
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')"
CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.headless=true"]
