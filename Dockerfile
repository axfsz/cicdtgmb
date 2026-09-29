FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Shanghai

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY bot.py /app/bot.py
COPY jobs.json /app/jobs.json

CMD ["python", "/app/bot.py"]
