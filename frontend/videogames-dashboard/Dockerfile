# Stage 1: Build
FROM node:20-alpine AS build
WORKDIR /app
ENV NODE_OPTIONS=--max-old-space-size=4096
ENV NG_CLI_ANALYTICS=false
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN echo "Iniciando ng build (puede tardar 1-3 min)..." && \
    npx ng build --configuration=production && \
    echo "ng build completado."

# Stage 2: Serve with nginx
FROM nginx:alpine
COPY --from=build /app/dist/videogames-dashboard/browser /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
