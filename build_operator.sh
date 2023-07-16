#!/bin/bash

docker build -t rs-operator:1.0 .
# docker push rs-operator:1.0

minikube image load rs-operator:1.0