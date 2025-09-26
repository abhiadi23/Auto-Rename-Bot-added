FROM python:3.10-slim

WORKDIR /app
COPY . /app/

# 
RUN apt-get update && apt-get install -y \
    gcc \
    libffi-dev \
    musl-dev \
    && rm -rf /var/lib/apt/lists/*

# python deps install karo
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD ["python", "bot.py"]