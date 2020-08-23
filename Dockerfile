FROM golang:1.15 AS build

ENV CGO_ENABLED 0
ENV GOOS linux
ENV GOPATH /go

COPY . /src
WORKDIR /src
RUN mkdir -p /out &&\
    go test ./... &&\
    go build -o /out/piedotbot ./cmd/piedotbot

FROM scratch
COPY --from=build /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt
COPY --from=build /out /
ENTRYPOINT [ "/piedotbot" ]
CMD []
