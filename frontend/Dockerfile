# Build context is the repo root: the theme imports ../packages/ui-theme.
# The output is static files, so build natively instead of under QEMU.
FROM --platform=$BUILDPLATFORM node:22-alpine AS build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY packages/ /app/packages/
COPY frontend/ ./

# Vite inlines VITE_* at build time; the client ID is public (it ships in the bundle).
ARG VITE_GOOGLE_CLIENT_ID=""
ENV VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID
RUN npm run build

FROM nginx:1.27-alpine

COPY frontend/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/frontend/dist /usr/share/nginx/html

EXPOSE 80
