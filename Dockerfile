FROM python:3.9.1-slim-buster
RUN mkdir /app
RUN mkdir /instance
ENV INSTANCE_PATH=/instance
COPY . /app
WORKDIR app
RUN python -m pip install -r requirements.txt
EXPOSE 80
ENTRYPOINT ["gunicorn", "-b", "0.0.0.0:80", "app:app"]
