FROM python

RUN mkdir -p /usr/my_app

WORKDIR /usr/my_app

COPY modules.txt ./
RUN pip install --no-cache-dir -r modules.txt

COPY . .

WORKDIR /usr/my_app/data_harvest

CMD [ "/bin/sh", "-c", "python sevenDays.py" ]
