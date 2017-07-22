FROM python:3

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /src/

CMD [ "python", "./src/main.py", "/srv/token.dat", "-s", "/srv/state.json" ]
