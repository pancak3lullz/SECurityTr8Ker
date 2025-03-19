# Use the official Python image from the Docker Hub
FROM python:3.9

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install the application in development mode to ensure imports work correctly
RUN pip install -e .

# Make the message script executable
RUN chmod +x /app/send_message.py

# Create a symbolic link to the script in /usr/local/bin for easier access
RUN ln -s /app/send_message.py /usr/local/bin/sectracker-message

# Define environment variable
ENV NAME SECurityTr8Ker
ENV PYTHONPATH=/app

# Run main.py when the container launches
CMD ["python", "main.py"]
