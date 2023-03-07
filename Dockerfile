FROM python:3.8-slim

WORKDIR /app
COPY requirements.txt ./
RUN apt update && apt -y install git && pip install --no-cache-dir -r requirements.txt && apt -y remove git && apt -y clean 
COPY camerafile ./camerafile
COPY setup.py ./setup.py
RUN pip install -e .

CMD [ "python", "./camerafile/cfm.py", "--no-progress", "organize", "--watch", "/dir1", "/dir2"]