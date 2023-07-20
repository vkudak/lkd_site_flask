# start by pulling the python image
FROM python:3.10.8-slim-buster

# copy the requirements file into the image
COPY ./requirements.txt /app/requirements.txt

# copy every content from the local file to the image
COPY . /app

# switch working directory
WORKDIR /app
#WORKDIR /
RUN ls

# install the dependencies and packages in the requirements file
RUN python3 -m pip install --upgrade pip

RUN ls
RUN python3 -m pip install -r requirements.txt

EXPOSE 8000

CMD ["gunicorn", "--bind" , "0.0.0.0:8000", "--workers", "1", "run:app", "--threads", "3"]


