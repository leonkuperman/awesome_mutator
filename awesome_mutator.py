from fastapi import FastAPI, Request
from pydantic import BaseModel
from kubernetes.client import V1Pod, V1ObjectMeta, V1PodSpec
from kubernetes import client, config
import base64
import json
import logging

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("awesome_mutator")

app = FastAPI()

# Function to check if a pod matches a given selector
def pod_matches_selector(pod: V1Pod, selector: str) -> bool:
    selector_dict = dict(pair.split("=") for pair in selector.split(","))
    matches = all(item in pod.metadata.labels.items() for item in selector_dict.items())
    logger.info(f"Checking if pod matches selector '{selector}': {matches}")
    return matches

# Helper function to escape JSON Patch paths
def escape_json_pointer(key: str) -> str:
    return key.replace("/", "~1")

# Function to create JSON patches for pod mutations
def create_json_patch(pod: V1Pod, rules: list) -> list:
    patches = []
    logger.info(f"Creating JSON patches for pod: {pod.metadata.name}")

    for rule in rules:
        if pod_matches_selector(pod, rule['podSelector']):
            logger.info(f"Pod matches rule '{rule['name']}': Applying mutations")

            # Ensure node_selector is not None
            node_selector = pod.spec.node_selector if pod.spec.node_selector else {}
            
            # If nodeSelector is empty, create a patch to add an empty object
            if not pod.spec.node_selector:
                patches.append({"op": "add", "path": "/spec/nodeSelector", "value": {}})
                logger.info("Added patch to create nodeSelector")

            # Remove specified node selectors
            for selector in rule['removeNodeSelectors']:
                if selector in node_selector:
                    patches.append({"op": "remove", "path": f"/spec/nodeSelector/{escape_json_pointer(selector)}"})
                    logger.info(f"Removing node selector '{selector}'")

            # Add specified node selectors
            for key, value in rule['addNodeSelectors'].items():
                escaped_key = escape_json_pointer(key)
                patches.append({"op": "add", "path": f"/spec/nodeSelector/{escaped_key}", "value": value})
                logger.info(f"Adding node selector '{key}: {value}'")

            # Add tolerations if specified
            if 'addTolerations' in rule:
                if not pod.spec.tolerations:
                    # If no tolerations exist, create an empty list
                    patches.append({"op": "add", "path": "/spec/tolerations", "value": []})
                    logger.info("Added patch to create tolerations list")
                
                for toleration in rule['addTolerations']:
                    # Escape keys in toleration to handle special characters
                    escaped_toleration = {escape_json_pointer(k): v for k, v in toleration.items()}
                    patches.append({"op": "add", "path": "/spec/tolerations/-", "value": escaped_toleration})
                    logger.info(f"Adding toleration: {escaped_toleration}")

            # Stop processing further rules after the first match
            logger.info(f"Stopping rule evaluation after applying rule '{rule['name']}'")
            break

    logger.info(f"Generated patches: {patches}")
    return patches

# Define the request model for the admission webhook
class AdmissionReviewRequest(BaseModel):
    request: dict
    apiVersion: str
    kind: str

# Helper function to filter fields for V1ObjectMeta
def filter_object_meta(data: dict) -> dict:
    valid_keys = V1ObjectMeta.__init__.__code__.co_varnames
    filtered_data = {k: v for k, v in data.items() if k in valid_keys}
    logger.info(f"Filtered object metadata: {filtered_data}")
    return filtered_data

# Helper function to filter fields for V1PodSpec
def filter_pod_spec(data: dict) -> dict:
    valid_keys = V1PodSpec.__init__.__code__.co_varnames
    filtered_data = {k: v for k, v in data.items() if k in valid_keys}
    logger.info(f"Filtered pod spec: {filtered_data}")
    return filtered_data

# Function to load mutation rules from ConfigMap
def load_mutation_rules() -> list:
    try:
        config.load_incluster_config()  # Use in-cluster configuration
    except config.ConfigException:
        config.load_kube_config()  # Fallback to local kubeconfig for testing

    v1 = client.CoreV1Api()

    try:
        # Fetch the ConfigMap
        config_map = v1.read_namespaced_config_map("mutation-rules-configmap", "default")
        rules_json = config_map.data.get("rules.json", "[]")  # Default to an empty list if not found
        rules = json.loads(rules_json)
        logger.info(f"Loaded mutation rules from ConfigMap: {rules}")
        return rules
    except Exception as e:
        logger.error(f"Error loading mutation rules from ConfigMap: {e}")
        return []  # Fail open with no rules if an error occurs

@app.on_event("startup")
async def startup_event():
    # Load mutation rules from ConfigMap on startup
    global mutation_rules
    mutation_rules = load_mutation_rules()

@app.post("/mutate")
async def mutate(request: AdmissionReviewRequest):
    request_data = request.request
    logger.info("Received mutation request")

    try:
        # Extract and filter metadata and spec fields for the V1Pod constructor
        pod_metadata = filter_object_meta(request_data['object'].get('metadata', {}))
        pod_spec = filter_pod_spec(request_data['object'].get('spec', {}))

        # Create a V1Pod object using the filtered metadata and spec
        pod = V1Pod(metadata=V1ObjectMeta(**pod_metadata), spec=V1PodSpec(**pod_spec))
        logger.info(f"Created V1Pod object for pod: {pod.metadata.name}")

        # Create JSON patches for the pod
        patches = create_json_patch(pod, mutation_rules)

        # Construct the response in the correct AdmissionReview format
        admission_response = {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": {
                "uid": request_data['uid'],
                "allowed": True,
                "patchType": "JSONPatch",
                "patch": base64.b64encode(json.dumps(patches).encode()).decode()
            }
        }
    except Exception as e:
        # Log the exception and fail open
        logger.error(f"Error processing mutation: {e}. Failing open to allow pod creation.")
        admission_response = {
            "apiVersion": "admission.k8s.io/v1",
            "kind": "AdmissionReview",
            "response": {
                "uid": request_data['uid'],
                "allowed": True
            }
        }

    logger.info("Sending admission response")
    return admission_response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("awesome_mutator:app", host="0.0.0.0", port=443, ssl_keyfile="key.pem", ssl_certfile="cert.pem")