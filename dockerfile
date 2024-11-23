# Use an official Python runtime as a parent image 1
FROM python:3.12-slim-bookworm

# Set the working directory in the container 1
WORKDIR /app

# Copy the current directory contents into the container at /app 1
COPY . /app/

# Install any needed packages specified in requirements.txt 1
RUN pip install --no-cache-dir -r requirements.txt

# Make port 80 available to the world outside this container 1
EXPOSE 80

# Create a volume for logs
VOLUME ["/app/logs"]

# Run main.py when the container launches 1
CMD ["python", "main.py"]