import logging
import json
import requests
import uuid
import copy

from ...core.events import handler
from ...core.events.types import Vulnerability, Event
from ..discovery.apiserver import ApiServer, ApiServerWithServiceAccountToken
from ...core.types import Hunter, ActiveHunter, KubernetesCluster
from ...core.types import RemoteCodeExec, AccessRisk, InformationDisclosure, UnauthenticatedAccess


""" Vulnerabilities """


class ServerApiAccess(Vulnerability, Event):
    """ The API Server port is accessible. Depending on your RBAC settings this could expose access to or control of your cluster. """
 
    def __init__(self, evidence, category):
        Vulnerability.__init__(self, KubernetesCluster, name="Access to server API", category=category)
        self.evidence = evidence


class ListPodsAndNamespaces(Vulnerability, Event):
    """ Accessing pods might give an attacker valuable information"""

    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Listing pods",
                               category=InformationDisclosure)
        self.evidence = evidence


class ListNamespaces(Vulnerability, Event):
    """ Accessing namespaces might give an attacker valuable information """

    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Listing namespaces",
                               category=InformationDisclosure)
        self.evidence = evidence


class ListRoles(Vulnerability, Event):
    """ Accessing roles might give an attacker valuable information """

    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Listing roles",
                               category=InformationDisclosure)
        self.evidence = evidence


class ListClusterRoles(Vulnerability, Event):
    """ Accessing cluster roles might give an attacker valuable information """

    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Listing cluster roles",
                               category=InformationDisclosure)
        self.evidence = evidence


class CreateANamespace(Vulnerability, Event):

    """ Creating a namespace might give an attacker an area with default (exploitable) permissions to run pods in.
    """
    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Created a namespace",
                               category=AccessRisk)
        self.evidence = evidence


class DeleteANamespace(Vulnerability, Event):

    """ Deleting a namespace might give an attacker the option to affect application behavior """
    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Delete a namespace",
                               category=AccessRisk)
        self.evidence = evidence


class CreateARole(Vulnerability, Event):
    """ Creating a role might give an attacker the option to harm the normal behavior of newly created pods
     within the specified namespaces.
    """

    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Created a role",
                               category=AccessRisk)
        self.evidence = evidence


class CreateAClusterRole(Vulnerability, Event):
    """ Creating a cluster role might give an attacker the option to harm the normal behavior of newly created pods
     across the whole cluster
    """

    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Created a cluster role",
                               category=AccessRisk)
        self.evidence = evidence


class PatchARole(Vulnerability, Event):
    """ Patching a role might give an attacker the option to create new pods with custom roles within the
    specific role's namespace scope
    """

    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Patched a role",
                               category=AccessRisk)
        self.evidence = evidence


class PatchAClusterRole(Vulnerability, Event):
    """ Patching a cluster role might give an attacker the option to create new pods with custom roles within the whole
    cluster scope.
    """

    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Patched a cluster role",
                               category=AccessRisk)
        self.evidence = evidence


class DeleteARole(Vulnerability, Event):
    """ Deleting a role might allow an attacker to affect access to resources in the namespace"""

    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Deleted a role",
                               category=AccessRisk)
        self.evidence = evidence


class DeleteAClusterRole(Vulnerability, Event):
    """ Deleting a cluster role might allow an attacker to affect access to resources in the cluster"""

    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Deleted a cluster role",
                               category=AccessRisk)
        self.evidence = evidence


class CreateAPod(Vulnerability, Event):
    """ Creating a new pod allows an attacker to run custom code"""

    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Created A Pod",
                               category=AccessRisk)
        self.evidence = evidence


class CreateAPrivilegedPod(Vulnerability, Event):
    """ Creating a new PRIVILEGED pod would gain an attacker FULL CONTROL over the cluster"""

    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Created A PRIVILEGED Pod",
                               category=AccessRisk)
        self.evidence = evidence


class PatchAPod(Vulnerability, Event):
    """ Patching a pod allows an attacker to compromise and control it """

    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Patched A Pod",
                               category=AccessRisk)
        self.evidence = evidence


class DeleteAPod(Vulnerability, Event):
    """ Deleting a pod allows an attacker to disturb applications on the cluster """

    def __init__(self, evidence):
        Vulnerability.__init__(self, KubernetesCluster, name="Deleted A Pod",
                               category=AccessRisk)
        self.evidence = evidence


class ApiServerPassiveHunterFinished(Event):
    def __init__(self, namespaces):
        self.namespaces = namespaces


# Passive Hunter
@handler.subscribe(ApiServer)
class AccessApiServer(Hunter):
    """ API Server Hunter
    """

    def __init__(self, event):
        self.event = event
        self.path = "https://{}:{}".format(self.event.host, self.event.port)
        self.headers = {}
        self.category = UnauthenticatedAccess

    def access_api_server(self):
        logging.debug('Passive Hunter is attempting to access the API at {host}:{port}'.format(host=self.event.host, 
            port=self.event.port))
        try:
            r = requests.get("{path}/api".format(path=self.path), headers=self.headers, verify=False)
            if r.status_code == 200 and r.content != '':
                return r.content
        except requests.exceptions.ConnectionError:
            pass
        return False

    def get_items(self, path):
        try: 
            items = []
            r = requests.get(path, headers=self.headers, verify=False)
            if r.status_code ==200:
                resp = json.loads(r.content)
                for item in resp["items"]:
                    items.append(item["metadata"]["name"])
                return items
        except (requests.exceptions.ConnectionError, KeyError):
            pass
        
        return None

    def get_pods(self, namespace=None):
        pods = []
        try:
            if namespace is None:
                r = requests.get("{path}/api/v1/pods".format(path=self.path),
                               headers=self.headers, verify=False)
            else:
                r = requests.get("{path}/api/v1/namespaces/{namespace}/pods".format(path=self.path),
                               headers=self.headers, verify=False)
            if r.status_code == 200:
                resp = json.loads(r.content)
                for item in resp["items"]:
                    name = item["metadata"]["name"].encode('ascii', 'ignore')
                    namespace = item["metadata"]["namespace"].encode('ascii', 'ignore')
                    pods.append({'name': name, 'namespace': namespace})

                return pods
        except (requests.exceptions.ConnectionError, KeyError):
            pass
        return None

    def get_namespaces(self):
        return self.get_items("{path}/api/v1/namespaces".format(path=self.path))

    def get_cluster_roles(self):
        return self.get_items("{path}/apis/rbac.authorization.k8s.io/v1/clusterroles".format(path=self.path))

    def get_roles(self):
        return self.get_items("{path}/apis/rbac.authorization.k8s.io/v1/roles".format(path=self.path))

    def execute(self):
        api = self.access_api_server()
        if api:
            self.publish_event(ServerApiAccess(api, self.category))

        namespaces = self.get_namespaces()
        if namespaces:
            self.publish_event(ListNamespaces(namespaces))

        pods = self.get_pods()
        if pods:
            self.publish_event(ListPodsAndNamespaces(pods))

        roles = self.get_roles()
        if roles:
            self.publish_event(ListRoles(roles))

        cluster_roles = self.get_cluster_roles()
        if cluster_roles:
            self.publish_event(ListClusterRoles(cluster_roles))

        # If we have a service account token, this event should get triggered twice - once with and once without
        # the token
        self.publish_event(ApiServerPassiveHunterFinished(namespaces))

@handler.subscribe(ApiServerWithServiceAccountToken)
class AccessApiServerWithToken(AccessApiServer):
    """ API Server Hunter
    Accessing the API server using the service account token obtained from a compromised pod
    """

    def __init__(self, event):
        super(AccessApiServerWithToken, self).__init__(event)
        assert self.event.auth_token != ''
        self.headers = {'Authorization': 'Bearer ' + self.event.auth_token}
        self.category = InformationDisclosure


# Active Hunter
@handler.subscribe(ApiServerPassiveHunterFinished)
class AccessApiServerActive(ActiveHunter, AccessApiServer):
    """API server hunter
    Accessing the api server might grant an attacker full control over the cluster
    """

    def __init__(self, event):
        self.event = event
        self.path = "https://{}:{}".format(self.event.host, self.event.port)

    def create_item(self, path, name, data):
        headers = {
            'Content-Type': 'application/json'
        }
        if self.event.auth_token:
            headers['Authorization'] = 'Bearer {token}'.format(token=self.event.auth_token)

        try:
            res = requests.post(path.format(name=name), verify=False, data=data, headers=headers)
            if res.status_code in [200, 201, 202]: 
                parsed_content = json.loads(res.content)
                return parsed_content['metadata']['name']
        except (requests.exceptions.ConnectionError, KeyError):
            pass
        return None

    def patch_item(self, path, data):
        headers = {
            'Content-Type': 'application/json-patch+json'
        }
        if self.event.auth_token:
            headers['Authorization'] = 'Bearer {token}'.format(token=self.event.auth_token)
        try:
            res = requests.patch(path, headers=headers, verify=False, data=data)
            if res.status_code not in [200, 201, 202]: 
                return None
            parsed_content = json.loads(res.content)
            # TODO is there a patch timestamp we could use?
            return parsed_content['metadata']['namespace']
        except (requests.exceptions.ConnectionError, KeyError):
            pass
        return None

    def delete_item(self, path):
        headers = {}
        if self.event.auth_token:
            headers['Authorization'] = 'Bearer {token}'.format(token=self.event.auth_token)
        try:
            res = requests.delete(path, headers=headers, verify=False)
            if res.status_code in [200, 201, 202]: 
                parsed_content = json.loads(res.content)
                return parsed_content['metadata']['deletionTimestamp']
        except (requests.exceptions.ConnectionError, KeyError):
            pass
        return None

    def create_a_pod(self, namespace, is_privileged):
        privileged_value = ',"securityContext":{"privileged":true}' if is_privileged else ''
        random_name = (str(uuid.uuid4()))[0:5]
        json_pod = \
            """
                {{"apiVersion": "v1",
                "kind": "Pod",
                "metadata": {{
                    "name": "{random_name}"
                }},
                "spec": {{
                    "containers": [
                        {{
                            "name": "{random_name}",
                            "image": "nginx:1.7.9",
                            "ports": [
                                {{
                                    "containerPort": 80
                                }}
                            ]
                            {is_privileged_flag}
                        }}
                    ]
                }}
            }}
            """.format(random_name=random_name, is_privileged_flag=privileged_value)
        return self.create_item(path="{path}/api/v1/namespaces/{namespace}/pods".format(
                                path=self.path, namespace=namespace), name=random_name, data=json_pod)

    def delete_a_pod(self, namespace, pod_name):
        delete_timestamp = self.delete_item("{path}/api/v1/namespaces/{namespace}/pods/{name}".format(
                                          path=self.path, name=pod_name, namespace=namespace))
        if delete_timestamp is None:
            logging.error("Created pod {name} in namespace {namespace} but unable to delete it".format(name=pod_name, namespace=namespace))
        return delete_timestamp

    def patch_a_pod(self, namespace, pod_name):
        data = '[{ "op": "add", "path": "/hello", "value": ["world"] }]'
        return self.patch_item(path="{path}/api/v1/namespaces/{namespace}/pods/{name}".format(
                                 path=self.path, namespace=namespace, name=pod_name),
                                 data=data)

    def create_namespace(self):
        random_name = (str(uuid.uuid4()))[0:5]
        json = '{{"kind":"Namespace","apiVersion":"v1","metadata":{{"name":"{random_str}","labels":{{"name":"{random_str}"}}}}}}'.format(random_str=random_name)
        return self.create_item(path="{path}/api/v1/namespaces".format(path=self.path), name=random_name, data=json)
        
    def delete_namespace(self, namespace):
        delete_timestamp = self.delete_item("{path}/api/v1/namespaces/{name}".format(path=self.path, name=namespace))
        if delete_timestamp is None:
            logging.error("Created namespace {namespace} but unable to delete it".format(namespace=namespace))
        return delete_timestamp

    def create_a_role(self, namespace):
        name = (str(uuid.uuid4()))[0:5]
        role = """{{
                          "kind": "Role",
                          "apiVersion": "rbac.authorization.k8s.io/v1",
                          "metadata": {{
                            "namespace": "{namespace}",
                            "name": "{random_str}"
                          }},
                          "rules": [
                            {{
                              "apiGroups": [
                                ""
                              ],
                              "resources": [
                                "pods"
                              ],
                              "verbs": [
                                "get",
                                "watch",
                                "list"
                              ]
                            }}
                          ]
                        }}""".format(random_str=name, namespace=namespace)
        return self.create_item(path="{path}/apis/rbac.authorization.k8s.io/v1/namespaces/{namespace}/roles".format(
                                path=self.path, namespace=namespace), name=name, data=role)
        
    def create_a_cluster_role(self):
        name = (str(uuid.uuid4()))[0:5]
        cluster_role = """{{
                      "kind": "ClusterRole",
                      "apiVersion": "rbac.authorization.k8s.io/v1",
                      "metadata": {{
                        "name": "{random_str}"
                      }},
                      "rules": [
                        {{
                          "apiGroups": [
                            ""
                          ],
                          "resources": [
                            "pods"
                          ],
                          "verbs": [
                            "get",
                            "watch",
                            "list"
                          ]
                        }}
                      ]
                    }}""".format(random_str=name)
        return self.create_item(path="{path}/apis/rbac.authorization.k8s.io/v1/clusterroles".format(
                               path=self.path), name=name, data=cluster_role)

    def delete_a_role(self, namespace, name):
        delete_timestamp = self.delete_item("{path}/apis/rbac.authorization.k8s.io/v1/namespaces/{namespace}/roles/{role}".format(
            path=self.path, name=namespace, role=name))
        if delete_timestamp is None:
            logging.error("Created role {name} in namespace {namespace} but unable to delete it".format(name=name, namespace=namespace))
        return delete_timestamp

    def delete_a_cluster_role(self, name):
        delete_timestamp = self.delete_item("{path}/apis/rbac.authorization.k8s.io/v1/clusterroles/{role}".format(
            path=self.path, role=name))
        if delete_timestamp is None:
            logging.error("Created cluster role {name} but unable to delete it".format(name=name))
        return delete_timestamp

    def patch_a_role(self, namespace, role):
        data = '[{ "op": "add", "path": "/hello", "value": ["world"] }]'
        return self.patch_item(path="{path}/apis/rbac.authorization.k8s.io/v1/namespaces/{namespace}/roles/{name}".format(
                                path=self.path, name=role, namespace=namespace),
                                data=data)

    def patch_a_cluster_role(self, cluster_role):
        data = '[{ "op": "add", "path": "/hello", "value": ["world"] }]'
        return self.patch_item(path="{path}/apis/rbac.authorization.k8s.io/v1/clusterroles/{name}".format(
                                path=self.path, name=cluster_role),
                                data=data)

    def execute(self):
        namespace = self.create_namespace()
        if namespace:
            self.publish_event(CreateANamespace('new namespace name: {name}'.format(name=namespace)))
            delete_timestamp = self.delete_namespace(namespace)
            if delete_timestamp:
                self.publish_event(DeleteANamespace(delete_timestamp))

        cluster_role = self.create_a_cluster_role()
        if cluster_role:
            self.publish_event(CreateAClusterRole('Cluster role name:  {name}'.format(name=cluster_role)))

            patch_evidence = self.patch_a_cluster_role(cluster_role)
            if patch_evidence:
                self.publish_event(PatchAClusterRole('Patched Cluster Role Name: {name}  Patch evidence: {patch_evidence}'.format(
                    name=cluster_role, patch_evidence=patch_evidence)))

            delete_timestamp = self.delete_a_cluster_role(cluster_role)
            if delete_timestamp:
                self.publish_event(DeleteAClusterRole('Cluster role {name} deletion time {delete_timestamp}'.format(
                                                        name=cluster_role, delete_timestamp=delete_timestamp)))

        #  Try attacking all the namespaces we know about
        for namespace in self.event.namespaces:
            # Try creating and deleting a privileged pod
            pod_name = self.create_a_pod(namespace, True)
            if pod_name:
                self.publish_event(CreateAPrivilegedPod('Pod Name: {pod_name}  Namespace: {namespace}'.format(
                                                pod_name=pod_name, namespace=namespace)))
                delete_time = self.delete_a_pod(namespace, pod_name)
                if delete_time:
                    self.publish_event(DeleteAPod('Pod Name: {pod_name}  deletion time: {delete_time}'.format(
                                                pod_name=pod_name, delete_evidence=delete_time)))
            
            # Try creating, patching and deleting an unprivileged pod
            pod_name = self.create_a_pod(namespace, False)
            if pod_name:
                self.publish_event(CreateAPod('Pod Name: {pod_name}  Namespace: {namespace}'.format(
                                                pod_name=pod_name, namespace=namespace)))

                patch_evidence = self.patch_a_pod(namespace, pod_name)
                if patch_evidence:
                    self.publish_event(PatchAPod('Pod Name: {pod_name}  Namespace: {namespace}  Patch evidence: {patch_evidence}'.format(
                                                    pod_name=pod_name, namespace=namespace,
                                                    patch_evidence=patch_evidence)))

                delete_time = self.delete_a_pod(namespace, pod_name)
                if delete_time:
                    self.publish_event(DeleteAPod('Pod Name: {pod_name}  Namespace: {namespace}  Delete time: {delete_time}'.format(
                                                    pod_name=pod_name, namespace=namespace, delete_time=delete_time)))

            # Roles Api Calls:
            role = self.create_a_role(namespace)
            if role:
                self.publish_event(CreateARole('Role name:  {name}'.format(name=role)))

                patch_evidence = self.patch_a_role(namespace, role)
                if patch_evidence:
                    self.publish_event(PatchARole('Patched Role Name: {name}  Namespace: {namespace}  Patch evidence: {patch_evidence}'.format(
                        name=role, namespace=namespace, patch_evidence=patch_evidence)))

                delete_time = self.delete_a_role(namespace, role)
                if delete_time:
                    self.publish_event(DeleteARole('Deleted role: {name}  Namespace: {namespace}  Delete time: {delete_time}'.format(
                                                    name=role, namespace=namespace, delete_time=delete_time)))


            #  Note: we are not binding any role or cluster role because
            # -- in certain cases it might effect the running pod within the cluster (and we don't want to do that).
