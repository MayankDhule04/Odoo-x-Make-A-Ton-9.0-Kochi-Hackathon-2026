FROM node:24-alpine

WORKDIR /app

# Install dependencies from the lockfile first so this layer stays cached until
# package.json or package-lock.json change.
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY . .

EXPOSE 5173

CMD ["npm", "run", "dev"]
