from typing import Any

import cattrs
from attrs import asdict, define


@define(auto_attribs=True, kw_only=True)
class Base:
    @classmethod
    def from_dict(cls, data: Any):
        return cattrs.structure(data, cls)

    def to_dict(self) -> Any:
        return asdict(self)
