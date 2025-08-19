# Use an official Python runtime as a parent image
FROM python:3.11-slim

# 安装 Java
RUN apt-get update -y
RUN apt-get install -y openjdk-21-jdk vim

ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
ENV PATH="${JAVA_HOME}/bin:${PATH}"

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's code into the container at /app
COPY . .

# Expose port 9900 to the outside world
EXPOSE 9900

# Command to run the application
CMD ["python", "main.py"]
