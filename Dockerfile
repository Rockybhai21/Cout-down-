# Use an official lightweight Python image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the necessary files
COPY bot.py requirements.txt start.sh ./

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Give execution permissions to the start script
RUN chmod +x start.sh

# Expose port 8080 for Koyeb compatibility
EXPOSE 8080

# Start the bot
CMD ["bash", "start.sh"]
