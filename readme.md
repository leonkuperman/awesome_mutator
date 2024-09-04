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