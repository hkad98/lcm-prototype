from __future__ import annotations

from pathlib import Path
from typing import Optional

from attrs import Factory, define, field
from gooddata_sdk import (
    CatalogDeclarativeAnalytics,
    CatalogDeclarativeModel,
    CatalogDeclarativeWorkspaceDataFilter,
    CatalogDeclarativeWorkspaceDataFilterSetting,
    CatalogDeclarativeWorkspaceModel,
    CatalogWorkspace,
    CatalogWorkspaceIdentifier,
)
from gooddata_sdk.catalog.workspace.declarative_model.workspace.workspace import CatalogDeclarativeWorkspace

from config import ADM_FOLDER, LDM_FOLDER, TENANTS_FOLDER, Config
from scripts.base import Base
from scripts.utils import get_workspace_identifier, structure_data_class

sdk = Config.sdk


@define(auto_attribs=True, kw_only=True)
class Model(Base):
    adm_name: Optional[str] = None
    ldm_name: Optional[str] = None
    data_source_id: Optional[str] = None
    adm: Optional[CatalogDeclarativeAnalytics] = None
    ldm: Optional[CatalogDeclarativeModel] = None

    def __attrs_post_init__(self):
        if self.adm_name:
            self.adm = sdk.catalog_workspace_content.load_analytics_model_from_disk(ADM_FOLDER / self.adm_name)
        if self.ldm_name:
            self.ldm = sdk.catalog_workspace_content.load_ldm_from_disk(LDM_FOLDER / self.ldm_name)
            if self.data_source_id:
                for dataset in self.ldm.ldm.datasets:
                    dataset.data_source_table_id.data_source_id = self.data_source_id

    @property
    def model(self) -> CatalogDeclarativeWorkspaceModel:
        ldm, adm = None, None
        if self.ldm:
            ldm = self.ldm.ldm
        if self.adm:
            adm = self.adm.analytics
        return CatalogDeclarativeWorkspaceModel(ldm=ldm, analytics=adm)


@define(auto_attribs=True, kw_only=True)
class WorkspaceDataFilters(Base):
    column_names: list[str] = field(factory=list)


@define(auto_attribs=True, kw_only=True)
class WorkspaceDataFiltersSettings(Base):
    column_name: str
    filter_values: list[str]


@define(auto_attribs=True, kw_only=True)
class Workspace(Base):
    name: str
    id: Optional[str] = field(default=Factory(lambda self: "_".join(self.name.lower().split()), takes_self=True))
    model: Optional[Model] = field(default=None)
    workspace_data_filters: Optional[WorkspaceDataFilters] = field(default=None)
    workspace_data_filters_settings: Optional[list[WorkspaceDataFiltersSettings]] = field(factory=list)
    children: Optional[list[Workspace]] = field(factory=list)
    tenants_name: Optional[str] = field(default=None)
    tenants: Optional[list[Tenants]] = field(factory=list, init=False)
    parent: Optional[str] = field(default=None, init=False)
    definition_folder_path: Optional[Path] = field(default=None, init=False, eq=False)

    def get_workspace(self, workspace_id: str) -> Optional[Workspace]:
        # Check children
        for child in self.children:
            if child.id == workspace_id:
                return child
        # Check tenants
        for tenant in self.tenants:
            if tenant.id == workspace_id:
                return tenant
        # Check their children
        for child in self.children:
            ret = child.get_workspace(workspace_id)
            if ret:
                return child
        return None

    def set_definition_folder_path(self, value: Path) -> None:
        self.definition_folder_path = value
        self.tenants = self.get_tenants()
        for child in self.children:
            child.set_definition_folder_path(value)
        for tenant in self.tenants:
            tenant.set_definition_folder_path(value)

    def __attrs_post_init__(self):
        for child in self.children:
            child.parent = self.id

    def put(self):
        sdk.catalog_workspace.create_or_update(self.catalog_workspace)
        if self.model:
            if self.model.ldm:
                sdk.catalog_workspace_content.put_declarative_ldm(self.id, self.model.ldm)
            if self.model.adm:
                sdk.catalog_workspace_content.put_declarative_analytics_model(self.id, self.model.adm)
        for child in self.children:
            child.put()
        for tenant in self.tenants:
            tenant.put()

    def get_tenants(self) -> list[Tenants]:
        if self.tenants_name:
            tenants = structure_data_class(
                self.definition_folder_path / TENANTS_FOLDER / self.tenants_name,
                list[Tenants],
            )
            for tenant in tenants:
                tenant.parent = self.id
            return tenants
        return []

    def fetch_workspaces(self) -> list[CatalogDeclarativeWorkspace]:
        workspace = CatalogDeclarativeWorkspace(id=self.id, name=self.name)
        if self.parent:
            workspace.parent = get_workspace_identifier(self.parent)
        if self.model:
            workspace.model = self.model.model
        yield workspace

        for child in self.children:
            yield from child.fetch_workspaces()

    def fetch_workspace_data_filters(
        self,
    ) -> list[CatalogDeclarativeWorkspaceDataFilter]:
        workspace_data_filters = []
        if self.workspace_data_filters is not None:
            for column_name in self.workspace_data_filters.column_names:
                title = f"WDF {column_name}"
                workspace_data_filter_id = title.lower().replace(" ", "-")
                wdf_o = CatalogDeclarativeWorkspaceDataFilter(
                    id=workspace_data_filter_id,
                    title=title,
                    column_name=column_name,
                    workspace_data_filter_settings=[],
                    workspace=get_workspace_identifier(self.id),
                )
                workspace_data_filters.append(wdf_o)

        for child in self.children:
            workspace_data_filters.extend(child.fetch_workspace_data_filters())
        return workspace_data_filters

    def fetch_workspace_data_filters_settings(
        self,
    ) -> dict[str, list[CatalogDeclarativeWorkspaceDataFilterSetting]]:
        workspace_data_filters_settings = {}
        for workspace_data_filter in self.workspace_data_filters_settings:
            title = f"WDF {self.id} {' '.join(workspace_data_filter.filter_values)}"
            workspace_data_filter_id = title.lower().replace(" ", "-")
            data_filter_object = CatalogDeclarativeWorkspaceDataFilterSetting(
                id=workspace_data_filter_id,
                title=title,
                filter_values=workspace_data_filter.filter_values,
                workspace=get_workspace_identifier(self.id),
            )
            key = workspace_data_filter.column_name
            if key not in workspace_data_filters_settings:
                workspace_data_filters_settings[key] = [data_filter_object]
            else:
                workspace_data_filters_settings[key].append(data_filter_object)
        for child in self.children:
            child_data_filters = child.fetch_workspace_data_filters_settings()
            for k, v in child_data_filters.items():
                if k in workspace_data_filters_settings:
                    workspace_data_filters_settings[k].extend(v)
                else:
                    workspace_data_filters_settings[k] = v
        for tenant in self.tenants:
            tenant_data_filters = tenant.fetch_workspace_data_filters_settings()
            for k, v in tenant_data_filters.items():
                if k in workspace_data_filters_settings:
                    workspace_data_filters_settings[k].extend(v)
                else:
                    workspace_data_filters_settings[k] = v
        return workspace_data_filters_settings

    @property
    def workspace_identifier(self) -> CatalogWorkspaceIdentifier:
        return CatalogWorkspaceIdentifier(id=self.id)

    @property
    def catalog_workspace(self) -> CatalogWorkspace:
        parent_id = self.parent if self.parent else None
        return CatalogWorkspace(self.id, self.name, parent_id)


@define(auto_attribs=True, kw_only=True)
class Tenants(Workspace):
    name: str
    id: Optional[str] = field(default=Factory(lambda self: "_".join(self.name.lower().split()), takes_self=True))
    workspace_data_filters_settings: Optional[list[WorkspaceDataFiltersSettings]] = field(factory=list)
    parent: Optional[str] = field(default=None, init=False)

    # Disabled Workspace attributes
    model: Optional[Model] = field(init=False, default=None)
    workspace_data_filters: Optional[WorkspaceDataFilters] = field(init=False, default=None)
    children: Optional[list[Workspace]] = field(init=False, factory=list)
    tenants: Optional[list[Tenants]] = field(init=False, factory=list)
    tenants_name: Optional[str] = field(init=False, default=None)

    def fetch_workspace_data_filters(
        self,
    ) -> list[CatalogDeclarativeWorkspaceDataFilter]:
        """
        Not supported for tenants.
        """
        return NotImplemented
