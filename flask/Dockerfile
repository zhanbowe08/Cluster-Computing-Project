FROM python
COPY ./flask /flask/
COPY ./frontend /frontend/
WORKDIR /flask/
RUN pip install --no-cache-dir -r requirements.txt
EXPOSE 8000
EXPOSE 5984
ENTRYPOINT ["./run_flask_gunicorn.sh"]
