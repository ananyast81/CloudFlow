FROM python:3.11-slim AS backend
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MPLBACKEND=Agg \
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 CLOUDFLOW_WORKSPACE=/workspace \
    MPLCONFIGDIR=/tmp/matplotlib
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 cloudflow && useradd --uid 10001 --gid cloudflow --create-home cloudflow \
    && mkdir /workspace && chown cloudflow:cloudflow /workspace
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=cloudflow:cloudflow api ./api
COPY --chown=cloudflow:cloudflow agents ./agents
COPY --chown=cloudflow:cloudflow shared ./shared
COPY --chown=cloudflow:cloudflow orchestrator ./orchestrator
COPY --chown=cloudflow:cloudflow scripts ./scripts
COPY --chown=cloudflow:cloudflow configs ./configs
USER cloudflow
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
