FROM tensorflow/tensorflow:2.1.0-gpu-py3

# install kubectl
RUN VERSION=$(curl -s https://storage.googleapis.com/kubernetes-release/release/stable.txt) && \
    curl -sfL https://storage.googleapis.com/kubernetes-release/release/$VERSION/bin/linux/amd64/kubectl -o /usr/bin/kubectl && \
    chmod +x /usr/bin/kubectl && \
    kubectl version --client --short

# install argo
RUN VERSION=v2.8.0 && \
    curl -sfL https://github.com/argoproj/argo/releases/download/$VERSION/argo-linux-amd64 -o /usr/bin/argo && \
    chmod +x /usr/bin/argo

# install required packages
RUN apt-get update && \
    apt-get -qq -y install \
        gir1.2-gtk-3.0 \
        git \
        gobject-introspection \
        libgirepository1.0-dev \
        libcairo2-dev \
        wget

# install golang
RUN add-apt-repository ppa:longsleep/golang-backports -y && \
    apt-get update && \
    apt-get -qq -y install golang-go

# install buildah
RUN . /etc/os-release && \
    echo "deb http://download.opensuse.org/repositories/devel:/kubic:/libcontainers:/stable/xUbuntu_${VERSION_ID}/ /" > /etc/apt/sources.list.d/devel:kubic:libcontainers:stable.list && \
    wget -nv https://download.opensuse.org/repositories/devel:kubic:libcontainers:stable/xUbuntu_${VERSION_ID}/Release.key -O Release.key && \
    apt-key add - < Release.key && \
    apt-get update && \
    apt-get -qq -y install buildah && \
    rm -rf /var/lib/apt/lists/* Release.key
RUN sed -i 's/driver = ""/driver = "vfs"/' /etc/containers/storage.conf

# setup git
RUN git config --global user.name Kubeflow && \
    git config --global user.email k8s@saschagrunert.de

# install python dependencies
COPY requirements.txt /
RUN pip install --no-cache-dir -r requirements.txt

ENTRYPOINT ["/bin/bash"]
