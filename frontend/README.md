# Poker ML Frontend

Vite + React frontend for the poker game UI.

## Run Locally

```bash
npm install
npm run dev
```

Open `http://localhost:3000`.

Local development automatically targets `ws://localhost:3002`. Set `VITE_WS_URL` only if you want to point the frontend at a different websocket endpoint.

## Quality Checks

```bash
npm run lint
npm run test
```

## Build

```bash
npm run build
```

The production bundle is generated in `dist/`.
