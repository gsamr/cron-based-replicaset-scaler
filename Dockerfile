FROM python:3.11

ADD rs-scaler.py /src/
RUN pip3 install kopf kubernetes  
CMD ["kopf","run", "/src/rs-scaler.py","--verbose"]