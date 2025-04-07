FROM node AS react-builder

RUN mkdir /build
WORKDIR /build
ARG CACHE_BUSTER=0 
RUN cd /build && git clone https://github.com/dpjl/cfm-ui-41.git \
    && cd cfm-ui-41 && git pull \
    && npm install --legacy-peer-deps \
    && npm run build


FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt ./
RUN apt update && apt -y install git libgl1 mesa-utils libglib2.0-0 && pip install --no-cache-dir -r requirements.txt && apt -y remove git && apt -y clean 
COPY camerafile ./camerafile
COPY setup.py ./setup.py
RUN pip install -e .

COPY --from=react-builder /build/cfm-ui-41/dist /app/www

ENV COMMAND=analyze
ENV DIR1=/dir1
ENV DIR2=/dir2
ENV IGNORE_DUPLICATES=true
ENV CACHE_PATH=/cache

CMD [ "python", "./camerafile/cfm.py" ]
