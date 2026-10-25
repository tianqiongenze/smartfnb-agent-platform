FROM 10.167.2.175:30500/base/nginx:1.27-alpine AS build
RUN apk add --no-cache nodejs npm
WORKDIR /src
COPY . .
RUN npm config set registry https://registry.npmmirror.com && npm install && npm run build

FROM 10.167.2.175:30500/base/nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /src/dist /usr/share/nginx/html
EXPOSE 80
