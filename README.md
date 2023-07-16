# cron-based-replicaset-scaler

This application is based on a crd and a kubernetes operator to scale up and down two replicasets deployed in two different namespaces. operator will create 4 seperator cronjobs to emit a scale up/down event stream when the desired cronjob time is met. using that event, the operator will patch the replica set 

Kopf is used to create the operator

to build the operator image run

```
./build_operator.sh
```

Running the script will build the operator image and then try to load the same image to a local minikube cluster. rest of the required k8s manifests are deployed using argocd

