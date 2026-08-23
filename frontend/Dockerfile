# Multi-stage build for the Next.js frontend (standalone output).
#
# Mainland-China builds: Docker Hub and the npm registry are slow or blocked there.
# Override at build time (infra/docker-compose.prod.yml forwards these from infra/.env):
#   --build-arg NODE_IMAGE=<mirror-host>/node:20-slim
#   --build-arg NPM_REGISTRY=https://registry.npmmirror.com
ARG NODE_IMAGE=node:20-slim
FROM ${NODE_IMAGE} AS builder
WORKDIR /app
ARG NPM_REGISTRY=https://registry.npmjs.org
# NEXT_PUBLIC_* values are baked into the client bundle at build time — setting them
# as container runtime env has no effect. Pass them as build args (compose forwards
# them from infra/.env).
ARG NEXT_PUBLIC_API_BASE=
ARG NEXT_PUBLIC_MEDIA_BASE=
ARG NEXT_PUBLIC_ICP_NUMBER=
ARG NEXT_PUBLIC_PSB_NUMBER=
ARG NEXT_PUBLIC_PSB_CODE=
ARG NEXT_PUBLIC_PSB_LOGO=
ENV NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE \
    NEXT_PUBLIC_MEDIA_BASE=$NEXT_PUBLIC_MEDIA_BASE \
    NEXT_PUBLIC_ICP_NUMBER=$NEXT_PUBLIC_ICP_NUMBER \
    NEXT_PUBLIC_PSB_NUMBER=$NEXT_PUBLIC_PSB_NUMBER \
    NEXT_PUBLIC_PSB_CODE=$NEXT_PUBLIC_PSB_CODE \
    NEXT_PUBLIC_PSB_LOGO=$NEXT_PUBLIC_PSB_LOGO
COPY package.json package-lock.json* ./
RUN npm config set registry "$NPM_REGISTRY" && npm install
COPY . .
RUN npm run build

FROM ${NODE_IMAGE} AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
