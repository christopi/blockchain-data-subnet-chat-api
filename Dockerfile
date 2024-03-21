# Use Python 3.11 slim image as the base
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the application files into the container
COPY . /app

# Install Python dependencies from requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Install jq and AWS CLI
# Update package lists, install jq, install AWS CLI via pip
RUN apt-get update && apt-get install -y jq && \
    pip install --no-cache-dir awscli && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Copy the entrypoint script into the container and make it executable
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

RUN alembic upgrade head

# Set the entrypoint to run the entrypoint script
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]

# Define the default command to run when starting the container
CMD ["bash"]


