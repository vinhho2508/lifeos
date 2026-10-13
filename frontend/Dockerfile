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

# The nginx image renders /etc/nginx/templates/*.template with envsubst on start.
# Defaults match docker-compose; on Render set BACKEND_URL=https://<backend>.onrender.com
# and BACKEND_HOST=<backend>.onrender.com.
ENV BACKEND_URL=http://backend:8000 \
    BACKEND_HOST=backend
COPY frontend/docker/default.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /app/frontend/dist /usr/share/nginx/html

EXPOSE 80
