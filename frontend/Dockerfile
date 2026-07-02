# Production frontend image: build the Vite bundle, serve it via nginx.
# VITE_* values are inlined at build time (see AIAAS DEPLOYMENT.md §2) — they
# MUST be passed as build args, not container env, or the bundle ships with
# localhost URLs baked in.
FROM node:20-alpine AS build
WORKDIR /app

ARG VITE_API_URL=/api/v1
ARG VITE_WS_URL=/ws
ARG VITE_GOOGLE_CLIENT_ID=
ARG VITE_GOOGLE_REDIRECT_URI=
ENV VITE_API_URL=$VITE_API_URL \
    VITE_WS_URL=$VITE_WS_URL \
    VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID \
    VITE_GOOGLE_REDIRECT_URI=$VITE_GOOGLE_REDIRECT_URI

COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget -qO- http://localhost/health || exit 1
CMD ["nginx", "-g", "daemon off;"]
