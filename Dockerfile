FROM tensorflow/tensorflow:2.1.0-gpu-py3

RUN VERSION=$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt) && \
    curl -sfL https://storage.googleapis.com/kubernetes-release/release/$VERSION/bin/linux/amd64/kubectl -o /usr/bin/kubectl && \
    chmod +x /usr/bin/kubectl && \
    kubectl version --client --short

RUN VERSION=v2.8.0-rc3 && \
    curl -sfL https://github.com/argoproj/argo/releases/download/$VERSION/argo-linux-amd64 -o /usr/bin/argo && \
    chmod +x /usr/bin/argo

RUN apt-get update \
    && apt-get install -y \
        gir1.2-gtk-3.0 \
        git \
        gobject-introspection \
        libgirepository1.0-dev \
        libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*

RUN git config --global user.name Kubeflow && \
    git config --global user.email k8s@saschagrunert.de

COPY requirements.txt /

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["/bin/bash"]
