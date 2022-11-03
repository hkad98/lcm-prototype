"""
IMPORTANT:
Do not move this file to another directory.
If you move it, you need to adapt the path below.
"""

import os
from pathlib import Path

from gooddata_sdk import CatalogDeclarativeDataSources, CatalogDeclarativeWorkspaces, GoodDataSdk

LAYOUTS_FOLDER = Path(__file__).parent / "layouts"
DEFINITIONS_FOLDER = Path(__file__).parent / "definitions"
SECRETS_FOLDER = Path(__file__).parent / "secrets"

ADM_FOLDER = LAYOUTS_FOLDER / "adm"
LDM_FOLDER = LAYOUTS_FOLDER / "ldm"
PDM_FOLDER = LAYOUTS_FOLDER / "pdm"
TEMPLATE_CONTENT = "template_content"
TENANTS_FOLDER = "tenants"
DEFINITION_FILE = "definition.yaml"


def clear_sdk():
    ds = CatalogDeclarativeDataSources(data_sources=[])
    ws = CatalogDeclarativeWorkspaces(workspaces=[], workspace_data_filters=[])

    Config.sdk.catalog_data_source.put_declarative_data_sources(declarative_data_sources=ds)
    Config.sdk.catalog_workspace.put_declarative_workspaces(workspace=ws)


class Config:
    __host = os.environ.get("TIGER_ENDPOINT", "http://localhost:3000")
    __token = os.environ.get("TIGER_API_TOKEN", "YWRtaW46Ym9vdHN0cmFwOmFkbWluMTIz")
    sdk = GoodDataSdk.create(host_=__host, token_=__token)
