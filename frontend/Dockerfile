FROM node:20.19.0

WORKDIR /app

RUN npm install --global pnpm@10.34.7
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/.npmrc ./
RUN pnpm install --frozen-lockfile

COPY frontend ./

EXPOSE 3000

CMD ["pnpm", "run", "dev"]
