# Use an official Node.js runtime as the base image
FROM node:14

# Set the working directory in the container
WORKDIR /app

# Copy the rest of your application code
# This copies the folder the Dockerfile is in
COPY . .

# Install project dependencies
RUN npm install

# Expose the port your React app will run on
# This doesn't map anything like "docker run -p 8080:3000" would, it's just metadata for docker
EXPOSE 3000

# Start your React app
CMD ["npm", "start"]