FROM python:3.12-slim-trixie

WORKDIR /app

COPY src/ /app/src
COPY requirements.txt /app/requirements.txt

RUN apt-get update && apt-get install -y libmariadb-dev gcc
RUN pip install --no-cache-dir -r /app/requirements.txt

CMD ["python", "src/mariadb_analyzer/cli.py"]