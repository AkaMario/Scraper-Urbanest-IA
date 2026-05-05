FROM node:20-alpine

WORKDIR /app/frontend

COPY frontend/package.json ./
RUN npm install --no-audit --no-fund

COPY frontend/ ./

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
