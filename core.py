from __future__ import annotations

from itertools import chain
from pathlib import Path

import yaml
from attrs import define, field
from gooddata_sdk import (
    CatalogDeclarativeDataSource,
    CatalogDeclarativeDataSources,
    CatalogDeclarativeWorkspaceDataFilters,
)
from gooddata_sdk.catalog.workspace.declarative_model.workspace.workspace import CatalogDeclarativeWorkspace
from jinja2 import Environment, FileSystemLoader

from config import DEFINITION_FILE, DEFINITIONS_FOLDER, SECRETS_FOLDER, TEMPLATE_CONTENT, Config, clear_sdk
from scripts.base import Base
from scripts.data_source import DataSource
from scripts.utils import load_yaml_file, load_yaml_files
from scripts.workspace import Workspace

sdk = Config.sdk


@define(auto_attribs=True, kw_only=True)
class Hierarchy(Base):
    workspaces: list[Workspace]
    data_sources: list[DataSource]
    definition_folder_path: str = field(eq=False)

    def __attrs_post_init__(self):
        for workspace in self.workspaces:
            workspace.set_definition_folder_path(Path(self.definition_folder_path))

    def get_workspace(self, workspace_id: str) -> Workspace:
        # Check top level workspaces first
        for workspace in self.workspaces:
            if workspace.id == workspace_id:
                return workspace
        # Check their children
        for workspace in self.workspaces:
            ret = workspace.get_workspace(workspace_id)
            if ret:
                return ret

    def fetch_all_workspace_data_filters(
        self,
    ) -> CatalogDeclarativeWorkspaceDataFilters:
        """
        FIX ME!!!
        This is not optimal
        """
        workspace_data_filters = []
        for workspace in self.workspaces:
            workspace_data_filters_temp = workspace.fetch_workspace_data_filters()
            data_filters_settings = workspace.fetch_workspace_data_filters_settings()
            for wdf in workspace_data_filters_temp:
                filtered_settings = data_filters_settings.get(wdf.column_name, [])
                data_filter_workspace = self.get_workspace(wdf.workspace.id)
                for data_filter_setting in filtered_settings:
                    if data_filter_workspace.get_workspace(data_filter_setting.workspace.id):
                        wdf.workspace_data_filter_settings.append(data_filter_setting)
            workspace_data_filters.extend(workspace_data_filters_temp)
        return CatalogDeclarativeWorkspaceDataFilters(workspace_data_filters=workspace_data_filters)

    def fetch_specific_workspace_data_filters(self, workspace_id: str) -> CatalogDeclarativeWorkspaceDataFilters:
        """
        FIX ME!!!
        This is not optimal
        """
        workspace_data_filters = []
        for workspace in self.workspaces:
            if workspace.id == workspace_id:
                workspace_data_filters_temp = workspace.fetch_workspace_data_filters()
                data_filters_settings = workspace.fetch_workspace_data_filters_settings()
                for wdf in workspace_data_filters_temp:
                    filtered_settings = data_filters_settings.get(wdf.column_name, [])
                    data_filter_workspace = self.get_workspace(wdf.workspace.id)
                    for data_filter_setting in filtered_settings:
                        if data_filter_workspace.get_workspace(data_filter_setting.workspace.id):
                            wdf.workspace_data_filter_settings.append(data_filter_setting)
                workspace_data_filters.extend(workspace_data_filters_temp)
        return CatalogDeclarativeWorkspaceDataFilters(workspace_data_filters=workspace_data_filters)

    def fetch_all_workspaces(self) -> chain[CatalogDeclarativeWorkspace]:
        """
        There can be a lot of workspaces and for that reason it is reasonable to return chain of workspaces.
        The change of workspaces can be easily iterated without memory limitation, but still it can be materialized.
        :return:
        """
        workspaces = []
        for workspace in self.workspaces:
            workspaces.append(workspace.fetch_workspaces())
        return chain.from_iterable(workspaces)

    def fetch_all_data_sources(self) -> list[CatalogDeclarativeDataSource]:
        data_sources = []
        for data_source in self.data_sources:
            data_sources.append(data_source.catalog_data_source)
        return data_sources

    @classmethod
    def from_definition(cls, definition_name: str):
        definition_folder_path = DEFINITIONS_FOLDER / definition_name
        definition_file_path = definition_folder_path / DEFINITION_FILE
        template_content_folder = definition_folder_path / TEMPLATE_CONTENT

        if template_content_folder.exists():
            environment = Environment(loader=FileSystemLoader(definition_folder_path))
            template = environment.get_template(DEFINITION_FILE)
            template_input = load_yaml_files(template_content_folder)
            data = yaml.safe_load(template.render(template_input))
        else:
            data = load_yaml_file(definition_file_path)
        return cls.from_dict(data | {"definition_folder_path": definition_folder_path})

    def put_data_sources(self):
        print(f"{'*' * 5} fetching data sources {'*' * 5}")
        data_sources = self.fetch_all_data_sources()
        print(f"{'*' * 5} put data sources {'*' * 5}")
        sdk.catalog_data_source.put_declarative_data_sources(
            declarative_data_sources=CatalogDeclarativeDataSources(data_sources=data_sources),
            credentials_path=SECRETS_FOLDER / "secret_ds_credentials.yaml",
        )

    def put_workspace_data_filters(self):
        print(f"{'*' * 5} fetching workspace data filters {'*' * 5}")
        workspace_data_filters = self.fetch_all_workspace_data_filters()
        print(f"{'*' * 5} put workspace data filters {'*' * 5}")
        sdk.catalog_workspace.put_declarative_workspace_data_filters(workspace_data_filters=workspace_data_filters)

    def put_specific_workspace_data_filters(self, workspace_id: str):
        print(f"{'*' * 5} fetching workspace data filters  {workspace_id=} put start {'*' * 5}")
        workspace_data_filters = self.fetch_specific_workspace_data_filters(workspace_id)
        print(f"{'*' * 5} put workspace data filters {workspace_id=} {'*' * 5}")
        sdk.catalog_workspace.put_declarative_workspace_data_filters(workspace_data_filters=workspace_data_filters)

    def put_workspaces(self):
        print(f"{'*' * 5} workspace put start {'*' * 5}")
        for workspace in self.workspaces:
            workspace.put()
        print(f"{'*' * 5} workspace put end {'*' * 5}")

    def put_workspace(self, workspace_id: str):
        print(f"{'*' * 5} workspace {workspace_id=} put start {'*' * 5}")
        for workspace in self.workspaces:
            if workspace.id == workspace_id:
                workspace.put()
        print(f"{'*' * 5} workspace {workspace_id=} put end {'*' * 5}")

    def put_all(self):
        clear_sdk()

        self.put_data_sources()
        self.put_workspaces()
        self.put_workspace_data_filters()

    def put_specific(self, workspace_id: str):
        """
        Put only top level parent and its subtree by workspace_id.
        """
        clear_sdk()

        self.put_data_sources()
        self.put_workspace(workspace_id)
        self.put_specific_workspace_data_filters(workspace_id)
