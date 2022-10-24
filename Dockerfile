# start by pulling the python image
FROM python:3.10.8-slim-buster

# copy the requirements file into the image
COPY ./requirements.txt /app/requirements.txt

# copy every content from the local file to the image
COPY . /app

# switch working directory
WORKDIR /app

# install the dependencies and packages in the requirements file
RUN python3 -m pip install --upgrade pip

RUN ls
RUN python3 -m pip install -r app/requirements.txt


