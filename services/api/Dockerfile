FROM golang:1.25-alpine AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -trimpath -o /api .
FROM alpine:3.22
RUN adduser -D -u 10001 app
USER app
COPY --from=build /api /api
ENTRYPOINT ["/api"]
