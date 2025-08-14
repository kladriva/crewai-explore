# --- build ---
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# Vite + Tailwind v4
RUN npm run build

# --- run ---
FROM nginx:1.27-alpine
# config nginx (proxy /api -> ai_agent:8000)
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
# fichiers statiques
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
