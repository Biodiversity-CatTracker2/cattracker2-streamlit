FROM python:3.10

EXPOSE ${TUNNEL_PORT}

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install -r requirements.txt
COPY *.py ./
COPY ./css /css
COPY ./DigiCertGlobalRootCA.crt.pem /usr/src/app/DigiCertGlobalRootCA.crt.pem
