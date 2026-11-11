# Multi-stage Dockerfile for AgroVaani Go Chaincode (Hyperledger Fabric CCaaS)

# Stage 1: Build Go chaincode binary
FROM golang:1.22-alpine AS builder

WORKDIR /app

ENV GOPROXY=https://proxy.golang.org,direct

# Copy Go module dependency files first for layer caching
COPY go.mod go.sum* ./
RUN go mod download

# Copy chaincode source files
COPY . .

# Compile chaincode binary to /app/agrovaani-cc
RUN CGO_ENABLED=0 GOOS=linux go build -o /app/agrovaani-cc main.go

# Stage 2: Minimal runtime container
FROM alpine:3.19

WORKDIR /app

# Copy compiled binary from build stage
COPY --from=builder /app/agrovaani-cc /app/agrovaani-cc

EXPOSE 9999

CMD ["/app/agrovaani-cc"]
