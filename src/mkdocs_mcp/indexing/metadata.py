"""Generic, configurable metadata classification.

Nothing here is organization- or site-specific. Behaviour is driven by
``Settings`` and an optional external topic taxonomy file:

    tenant   -> first path segment (optionally restricted to a configured list)
    doc_type -> runbook | tutorial | troubleshooting | reference | guide
                (by generic path conventions used across MkDocs sites)
    topics   -> matched against a configurable taxonomy; the default taxonomy
                lists common, vendor-neutral DevOps tools.

The default taxonomy intentionally contains only third-party product names
(Kubernetes, Terraform, …), never the deploying organization's names. Override
it entirely by pointing ``topics_file`` at your own YAML:

    topics:
      my-topic:
        paths: ["/my-topic/"]
        keywords: ["some phrase", "another"]
"""
from __future__ import annotations

from pathlib import Path

import yaml

from ..config import Settings

# Vendor-neutral default taxonomy: only third-party tool/product names.
DEFAULT_TOPICS: dict[str, dict[str, list[str]]] = {
    "kubernetes": {"paths": [], "keywords": ["kubernetes", "k8s", "kubectl", "pod", "namespace"]},
    "openshift": {"paths": [], "keywords": ["openshift", "okd", "oc login"]},
    "argocd": {"paths": ["/argo"], "keywords": ["argocd", "argo cd", "gitops"]},
    "helm": {"paths": [], "keywords": ["helm chart", "helm install", "values.yaml"]},
    "terraform": {"paths": [], "keywords": ["terraform", "tfstate", "opentofu", "hcl"]},
    "ansible": {"paths": [], "keywords": ["ansible", "playbook"]},
    "vault": {"paths": ["/vault/"], "keywords": ["vault", "secret", "kv engine"]},
    "keycloak": {"paths": [], "keywords": ["keycloak", "oidc", "openid", "saml", "sso"]},
    "gitlab": {"paths": ["/gitlab"], "keywords": ["gitlab", "ci/cd", "pipeline", "runner"]},
    "github": {"paths": [], "keywords": ["github", "github actions", "workflow"]},
    "docker": {"paths": [], "keywords": ["docker", "dockerfile", "container image"]},
    "nexus": {"paths": ["/nexus/"], "keywords": ["nexus", "artifact repository"]},
    "harbor": {"paths": [], "keywords": ["harbor", "image registry"]},
    "prometheus": {"paths": [], "keywords": ["prometheus", "alertmanager", "promql"]},
    "grafana": {"paths": [], "keywords": ["grafana", "dashboard"]},
    "aws": {"paths": [], "keywords": ["aws", "ec2", "s3 bucket", "iam", "amazon web services"]},
    "gcp": {"paths": [], "keywords": ["gcp", "google cloud", "gke"]},
    "azure": {"paths": [], "keywords": ["azure", "aks"]},
    "networking": {
        "paths": ["/networking/"],
        "keywords": ["network policy", "ingress", "egress", "load balancer", "dns"],
    },
    "troubleshooting": {
        "paths": ["/troubleshoot"],
        "keywords": ["troubleshoot", "debug", "incident"],
    },
}

# Generic doc-type conventions (path-based). These are common words, not names.
_TUTORIAL = ("/tutorials/", "/tutorial/")
_RUNBOOK = ("/runbooks/", "/runbook/")
_REFERENCE = ("/reference/", "/templates/", "/api/")


def _load_topics(settings: Settings) -> dict[str, dict[str, list[str]]]:
    if settings.topics_file:
        data = yaml.safe_load(Path(settings.topics_file).read_text(encoding="utf-8")) or {}
        topics = data.get("topics", data)
        if topics:
            return topics
    return DEFAULT_TOPICS


class Classifier:
    """Derives tenant / doc_type / topics from a page's path and content."""

    def __init__(self, settings: Settings) -> None:
        self.tenants = set(settings.tenants)
        self.topics = _load_topics(settings)
        self.vocab = sorted(self.topics.keys())
        # alias map: normalized variant -> canonical topic
        self._aliases = {t.replace("-", "").replace(" ", ""): t for t in self.vocab}

    def tenant_of(self, rel_path: str) -> str | None:
        if "/" not in rel_path:  # a top-level file has no tenant
            return None
        head = rel_path.split("/", 1)[0]
        if self.tenants:
            return head if head in self.tenants else None
        return head  # unrestricted: first segment is the tenant

    def doc_type_of(self, rel_path: str) -> str:
        p = "/" + rel_path.lower()
        if any(f in p for f in _RUNBOOK):
            return "runbook"
        if any(f in p for f in _TUTORIAL):
            return "tutorial"
        if "troubleshoot" in p:
            return "troubleshooting"
        if any(f in p for f in _REFERENCE):
            return "reference"
        return "guide"

    def is_runbook(self, rel_path: str) -> bool:
        p = "/" + rel_path.lower()
        return any(f in p for f in _RUNBOOK)

    def topics_of(self, rel_path: str, content: str) -> list[str]:
        p = "/" + rel_path.lower()
        haystack = (rel_path + "\n" + content).lower()
        found: list[str] = []
        for topic, rule in self.topics.items():
            paths = rule.get("paths") or []
            keywords = rule.get("keywords") or []
            if any(f in p for f in paths) or any(k in haystack for k in keywords):
                found.append(topic)
        return found

    def resolve_topic(self, topic: str) -> str | None:
        if not topic:
            return None
        key = topic.strip().lower().replace("-", "").replace(" ", "")
        builtins = {"k8s": "kubernetes", "okd": "openshift", "argo": "argocd", "tf": "terraform"}
        key = builtins.get(key, key)
        return self._aliases.get(key)
