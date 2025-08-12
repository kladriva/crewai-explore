FROM python:3.11-slim
WORKDIR /workspace
ENV PYTHONPATH=/workspace
COPY app/ /workspace/app/
RUN pip install --no-cache-dir -r /workspace/app/requirements.txt
CMD ["python", "-m", "app.crew"]
