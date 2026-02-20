# --- Stage 0: build Go environment with gnark dependencies ---
FROM docker.io/library/golang:1.21 AS gobuilder

# Pre-fetch Go module dependencies for gnark + picus_gnark
WORKDIR /workspace
RUN go mod init circuzz_picus_check && \
	go get github.com/Veridise/picus_gnark@latest && \
	go get github.com/consensys/gnark@v0.9.1 && \
	go get github.com/consensys/gnark-crypto@v0.12.1

# Create a stub file that imports the required packages so go mod tidy keeps them
RUN echo 'package main\n\
import (\n\
	_ "github.com/Veridise/picus_gnark"\n\
	_ "github.com/consensys/gnark/frontend"\n\
	_ "github.com/consensys/gnark-crypto/ecc"\n\
	_ "github.com/consensys/gnark/std/math/bits"\n\
	_ "github.com/consensys/gnark/std/math/cmp"\n\
)\n\
func main() {}' > stub.go && \
	go mod tidy


# --- Stage 1: final image based on the Picus base image ---
FROM docker.io/veridise/picus:base

# install Python 3.11 and download Go 1.21
RUN apt-get update && \
    apt-get install -y python3.11 wget && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
    wget https://go.dev/dl/go1.21.0.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.21.0.linux-amd64.tar.gz && \
    rm go1.21.0.linux-amd64.tar.gz && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# add Go to PATH
ENV PATH="/usr/local/go/bin:${PATH}"

# copy Go module cache from the build stage
COPY --from=gobuilder /go/pkg/mod /go/pkg/mod

# ensure go finds the pre-fetched module cache
ENV GOMODCACHE="/go/pkg/mod"

# create picus base project with pre-resolved go.mod and go.sum
COPY --from=gobuilder /workspace/go.mod /circuzz/gnark/picus_base/go.mod
COPY --from=gobuilder /workspace/go.sum /circuzz/gnark/picus_base/go.sum

# ------------------------------------- Setting up Picus -------------------------------------
RUN git clone https://github.com/Veridise/Picus.git /Picus

WORKDIR /Picus/
RUN raco make picus.rkt

# Create a command to run Picus
RUN ln -s /Picus/run-picus /usr/local/bin/run-picus

WORKDIR /app

CMD ["/bin/bash"]
