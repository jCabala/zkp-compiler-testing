# --- Stage 0: build circom at a specific commit ---
FROM circuzz/circom-base AS circombuild

# allow the caller to pin circom to a specific commit
ARG CIRCOM_COMMIT=HEAD

# build and install circom from the cloned repo provided by `circom-base`
RUN cd /circuzz/circom && \
	git fetch --all --tags && \
	git reset --hard ${CIRCOM_COMMIT} && \
	cargo install --path circom && \
	rm -rf /circuzz/circom


# --- Stage 1: final image based on the Picus base image ---
FROM docker.io/veridise/picus:base

# re-declare the build-arg so users can pass it while building (optional)
ARG CIRCOM_COMMIT

# install Python 3.11 to meet cli.py requirements
RUN apt-get update && \
	apt-get install -y python3.11 && \
	update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
	apt-get clean && \
	rm -rf /var/lib/apt/lists/*

# copy circom binary and supporting files from the build stage
# cargo installs binaries to /root/.cargo/bin by default in these images
COPY --from=circombuild /root/.cargo/bin /root/.cargo/bin
COPY --from=circombuild /circuzz /circuzz

# ensure circom is on PATH
ENV PATH="/root/.cargo/bin:${PATH}"

# ------------------------------------- Setting up Picus -------------------------------------
RUN git clone https://github.com/Veridise/Picus.git /Picus

WORKDIR /Picus/
RUN raco make picus.rkt

# Create a command to run Picus
RUN ln -s /Picus/run-picus /usr/local/bin/run-picus

WORKDIR /app

CMD ["/bin/bash"]
