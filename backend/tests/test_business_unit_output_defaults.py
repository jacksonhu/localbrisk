import yaml

from app.core.constants import ASSET_BUNDLE_CONFIG_FILE
from app.models.business_unit import AgentCreate, BusinessUnitCreate
from app.services.business_unit_service import BusinessUnitService


def test_create_business_unit_creates_default_output_bundle(tmp_path, monkeypatch):
    from app.core.config import settings

    catalogs_dir = tmp_path / "App_Data" / "Catalogs"
    monkeypatch.setattr(settings, "CATALOGS_DIR", catalogs_dir)

    service = BusinessUnitService()
    bu = service.create_business_unit(BusinessUnitCreate(name="demo_bu"))

    bundle_path = catalogs_dir / bu.name / "asset_bundles" / "output"
    assert bundle_path.exists()
    assert (bundle_path / "volumes").exists()

    bundle_config = yaml.safe_load((bundle_path / ASSET_BUNDLE_CONFIG_FILE).read_text(encoding="utf-8"))
    assert bundle_config["bundle_type"] == "local"


def test_create_agent_creates_output_local_volume(tmp_path, monkeypatch):
    from app.core.config import settings

    catalogs_dir = tmp_path / "App_Data" / "Catalogs"
    monkeypatch.setattr(settings, "CATALOGS_DIR", catalogs_dir)

    service = BusinessUnitService()
    service.create_business_unit(BusinessUnitCreate(name="demo_bu"))
    service.create_agent("demo_bu", AgentCreate(name="assistant"))

    agent_root = catalogs_dir / "demo_bu" / "agents" / "assistant"
    agent_output = agent_root / "output"
    assert agent_output.exists()
    assert (agent_root / "venv").exists()
    assert (agent_root / "venv" / "pyvenv.cfg").exists()

    volume_yaml = catalogs_dir / "demo_bu" / "asset_bundles" / "output" / "volumes" / "assistant.yaml"
    assert volume_yaml.exists()

    volume_config = yaml.safe_load(volume_yaml.read_text(encoding="utf-8"))
    assert volume_config["asset_type"] == "volume"
    assert volume_config["volume_type"] == "local"
    assert volume_config["storage_location"] == str(agent_output)


def test_business_unit_tree_includes_agent_output_files(tmp_path, monkeypatch):
    from app.core.config import settings

    catalogs_dir = tmp_path / "App_Data" / "Catalogs"
    monkeypatch.setattr(settings, "CATALOGS_DIR", catalogs_dir)

    service = BusinessUnitService()
    service.create_business_unit(BusinessUnitCreate(name="demo_bu"))
    service.create_agent("demo_bu", AgentCreate(name="assistant"))

    output_dir = catalogs_dir / "demo_bu" / "agents" / "assistant" / "output"
    (output_dir / "outputs").mkdir(parents=True, exist_ok=True)
    (output_dir / "outputs" / "result.txt").write_text("hello", encoding="utf-8")

    tree = service.get_business_unit_tree()
    bu_node = next(node for node in tree if node.name == "demo_bu")
    agent_node = next(node for node in bu_node.children if node.node_type == "agent" and node.name == "assistant")
    output_node = next(node for node in agent_node.children if node.node_type == "output")

    assert output_node.name == "output"
    outputs_dir = next(node for node in output_node.children if node.name == "outputs")
    assert outputs_dir.node_type == "folder"
    result_file = next(node for node in outputs_dir.children if node.name == "result.txt")
    assert result_file.node_type == "output_file"
    assert result_file.metadata.get("relative_path") == "outputs/result.txt"


def test_get_output_file_content_blocks_path_traversal(tmp_path, monkeypatch):
    from app.core.config import settings

    catalogs_dir = tmp_path / "App_Data" / "Catalogs"
    monkeypatch.setattr(settings, "CATALOGS_DIR", catalogs_dir)

    service = BusinessUnitService()
    service.create_business_unit(BusinessUnitCreate(name="demo_bu"))
    service.create_agent("demo_bu", AgentCreate(name="assistant"))

    output_dir = catalogs_dir / "demo_bu" / "agents" / "assistant" / "output"
    (output_dir / "safe.txt").write_text("safe-content", encoding="utf-8")

    result = service.get_output_file_content("demo_bu", "assistant", "safe.txt")
    assert result["content"] == "safe-content"

    try:
        service.get_output_file_content("demo_bu", "assistant", "../agent_spec.yaml")
        assert False, "expected ValueError"
    except ValueError:
        assert True
