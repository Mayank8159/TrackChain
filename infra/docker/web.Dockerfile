# Production container for the Next.js web app.

FROM node:20-alpine AS base
WORKDIR /app
RUN npm install -g pnpm

COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml turbo.json ./
COPY packages/shared ./packages/shared
COPY app ./app

RUN pnpm install --frozen-lockfile || pnpm install
RUN pnpm --filter @trackchain/app build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

COPY --from=base /app/app/.next/standalone ./
COPY --from=base /app/app/.next/static ./app/.next/static
COPY --from=base /app/app/public ./app/public

EXPOSE 3000
CMD ["node", "app/server.js"]
