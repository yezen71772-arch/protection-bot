FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libopus0 git && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY music_bot.py .

CMD ["python", "music_bot.py"]
