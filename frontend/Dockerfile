FROM node:22-alpine AS build
WORKDIR /app
# v1.6 — آدرس هستهٔ عامل «دانشگاه هوشمند من» در زمان ساخت در باندل تزریق می‌شود
ARG VITE_MSU_AGENT_URL=""
ENV VITE_MSU_AGENT_URL=$VITE_MSU_AGENT_URL
COPY package.json package-lock.json* ./
RUN npm ci || npm install --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 3000
CMD ["nginx", "-g", "daemon off;", "-c", "/etc/nginx/conf.d/default.conf"]
