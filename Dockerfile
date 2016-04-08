FROM python:3.5
MAINTAINER Greg Aker <greg@gregaker.net>

ADD ./ /app

WORKDIR /app
RUN pip install --upgrade pip aiohttp==0.21.4 cchardet==1.0.0 influxdb==2.12.0 \
    && rm -rf /var/lib/apt/lists/*

CMD ["python", "-u", "main.py"]

EXPOSE 8000

