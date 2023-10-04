FROM python:3.10.12

# Set the working directory to /app
WORKDIR /app

# Copy your project files into the container
COPY . /app

# Install dependencies
RUN pip install -r requirements.txt

# Expose the WebSocket port
EXPOSE 3002

# Define the command to run your WebSocket server
CMD ["python", "-u", "main.py"]
