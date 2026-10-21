FROM python:3.12-slim

WORKDIR /app
COPY requirements-lock.txt pyproject.toml README.md LICENSE ./
COPY . .
RUN pip install --no-cache-dir -r requirements-lock.txt \
 && pip install --no-cache-dir -e . --no-deps

ENV PORT=8501
EXPOSE 8501
CMD ["sh", "-c", "streamlit run host_app.py --server.port=${PORT} --server.address=0.0.0.0 --server.headless=true --browser.gatherUsageStats=false"]
