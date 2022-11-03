from pathlib import Path
from typing import Any, Optional

import cattrs
import yaml
from gooddata_sdk import CatalogWorkspaceIdentifier


def load_yaml_file(path: str | Path) -> Optional[list | dict[str, Any]]:
    if not path.exists():
        raise ValueError(f"Path {path} was not found.")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_yaml_files(path: Path) -> Any:
    res = {}
    for file in path.iterdir():
        res |= load_yaml_file(file)
    return res


def structure_data_class(path: str | Path, definition: Any) -> Any:
    data = load_yaml_file(path)
    return cattrs.structure(data, definition)


def get_workspace_identifier(workspace_id: str) -> CatalogWorkspaceIdentifier:
    return CatalogWorkspaceIdentifier(id=workspace_id)
