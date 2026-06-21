from mkdocs_mcp.config import Settings
from mkdocs_mcp.indexing.metadata import Classifier


def clf(**kw):
    return Classifier(Settings(**kw))


def test_tenant_unrestricted_first_segment():
    c = clf()
    assert c.tenant_of("platform/argocd/user-guide.md") == "platform"
    assert c.tenant_of("index.md") is None


def test_tenant_restricted_list():
    c = clf(tenants=["platform"])
    assert c.tenant_of("platform/x.md") == "platform"
    assert c.tenant_of("other/x.md") is None


def test_doc_type():
    c = clf()
    assert c.doc_type_of("platform/argocd/runbooks/x.md") == "runbook"
    assert c.doc_type_of("platform/nexus/tutorials/x.md") == "tutorial"
    assert c.doc_type_of("guides/troubleshoot-network.md") == "troubleshooting"
    assert c.doc_type_of("reference/api.md") == "reference"
    assert c.doc_type_of("platform/argocd/user-guide.md") == "guide"


def test_is_runbook():
    c = clf()
    assert c.is_runbook("platform/argocd/runbooks/x.md")
    assert not c.is_runbook("platform/argocd/user-guide.md")


def test_topics_from_path_and_keywords():
    c = clf()
    assert "argocd" in c.topics_of("platform/argocd/user-guide.md", "gitops content")
    assert "kubernetes" in c.topics_of("x.md", "deploy a pod with kubectl")
    assert "networking" in c.topics_of("platform/networking/x.md", "")


def test_resolve_topic_aliases():
    c = clf()
    assert c.resolve_topic("argo") == "argocd"
    assert c.resolve_topic("k8s") == "kubernetes"
    assert c.resolve_topic("okd") == "openshift"
    assert c.resolve_topic("nonsense") is None


def test_topics_file_override(tmp_path):
    f = tmp_path / "topics.yml"
    f.write_text("topics:\n  widgets:\n    paths: ['/widgets/']\n    keywords: ['widget']\n")
    c = clf(topics_file=str(f))
    assert c.vocab == ["widgets"]
    assert "widgets" in c.topics_of("x.md", "a widget here")
