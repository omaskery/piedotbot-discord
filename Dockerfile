FROM python:3

COPY Pipfile ./
RUN pip update

COPY . /src/

CMD [ "python", "-u", "./src/main.py", "/srv/token.dat" ]
