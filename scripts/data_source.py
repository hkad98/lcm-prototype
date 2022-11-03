from typing import Optional

from attrs import define
from gooddata_sdk import CatalogDeclarativeDataSource

from config import PDM_FOLDER, Config
from scripts.base import Base

sdk = Config.sdk


@define(auto_attribs=True, kw_only=True)
class DataSource(Base):
    # Mandatory
    id: str
    name: str
    type: str
    schema: str

    # Optional - there are more
    url: Optional[str]
    username: Optional[str]
    pdm: Optional[str]

    @property
    def catalog_data_source(self) -> CatalogDeclarativeDataSource:
        self_as_dict = self.to_dict()
        self_as_dict.pop("pdm", None)
        data_source = CatalogDeclarativeDataSource.from_dict(self_as_dict, camel_case=False)
        if self.pdm is not None:
            data_source.pdm = sdk.catalog_data_source.load_pdm_from_disk(PDM_FOLDER / self.pdm)
        return data_source
