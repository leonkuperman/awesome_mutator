# Awesome Mutator

**Awesome Mutator** is a Kubernetes mutating webhook that dynamically modifies pod specifications based on custom rules defined in a ConfigMap. It can add or remove node selectors, tolerations, and other configurations to match specific conditions.

## Features

- **Dynamic Mutations**: Modify pod specifications on-the-fly based on configurable rules.
- **Node Selectors and Tolerations**: Add or remove node selectors and tolerations to influence pod scheduling.
- **ConfigMap Driven**: Easily update mutation rules without changing the webhook code.
- **Fail-Open Mechanism**: Ensures that pod creation continues even if the webhook encounters errors.

## Prerequisites

- **Kubernetes Cluster**: A running Kubernetes cluster.
- **kubectl**: Command-line tool to interact with the Kubernetes cluster.
- **Docker**: To build and manage container images.
- **Kubernetes Python Client**: Used to interact with the Kubernetes API.

## Setup and Deployment
- You can pull the pre-built docker image from: https://hub.docker.com/repository/docker/lkup77/awesome_mutator/general

## Apply the k8s scripts in the following order
- kubectl apply -f k8s

This will create the needed rbac, service, deployment and webhook along with a sample configuration that you can change in *awesome-mutator-config-map.yaml* 

You should be able to see the startup logs as follows:

```
INFO:awesome_mutator:Loaded mutation rules from ConfigMap: [{'name': 'rule1', 'podSelector': 'app=myapp,environment=prod', 'removeNodeSelectors': ['disktype'], 'addNodeSelectors': {'scheduling.cast.ai/node-template': 'test-mut-nt'}}, {'name': 'remove-agentpool-for-canyon', 'podSelector': 'app=canyon', 'removeNodeSelectors': ['agentpool'], 'addNodeSelectors': {'scheduling.cast.ai/node-template': 'test-mut-nt-3'}, 'addTolerations': [{'key': 'scheduling.cast.ai/node-template', 'operator': 'Equal', 'value': '', 'effect': 'NoSchedule'}]}]
INFO:     Application startup complete.
```
The k8s folder also contains 2 test pods with various labels and node selectors. Once the webhook is up, it will mutate according to the rules in the config map.

## Rules

- Rules stop on first match
- Rules are matched by label selector using *podSelector* (and operation)
- Rules will remove NodeSelecor by name using *removeNodeSelectors*
- Rules will add NodeSelector using details of *addNodeSelectors*
- Rules will add Tolerations using the details of *addTolerations*
