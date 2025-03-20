FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt ./
RUN apt update && apt -y install git && pip install --no-cache-dir -r requirements.txt && apt -y remove git && apt -y clean 
COPY camerafile ./camerafile
COPY setup.py ./setup.py
RUN pip install -e .

ENV COMMAND=analyze
ENV DIR1=/dir1
ENV DIR2=/dir2
ENV IGNORE_DUPLICATES=true
ENV CACHE_PATH=/cache

CMD [ "python", "./camerafile/cfm.py" ]