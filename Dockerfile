# start by pulling the python image
FROM python:3.10.8-slim-buster

# copy the requirements file into the image
COPY ./requirements.txt /app/requirements.txt

# switch working directory
WORKDIR /

# install the dependencies and packages in the requirements file
RUN pip install -r requirements.txt

CMD ["ls"]

# copy every content from the local file to the image
COPY . .
