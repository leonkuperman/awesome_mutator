#! /bin/bash

kubectl port-forward service/awesome-mutator-service 443:443 -n default