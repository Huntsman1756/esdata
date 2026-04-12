FROM node:22-slim AS base

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json ./
RUN npm ci

# Copy source
COPY . .

# Build
ENV NODE_ENV=production
RUN npm run build

# Start
CMD ["npm", "start"]
