import dataclasses
import json
import sys
import zipfile
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any
from typing import Dict
from typing import Generic
from typing import List
from typing import Optional
from typing import Tuple
from typing import TYPE_CHECKING
from typing import TypeVar

import marshmallow
from marshmallow_dataclass import class_schema
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from packaging.utils import NormalizedName
from packaging.version import Version

if TYPE_CHECKING:
    from _typeshed import StrPath
else:
    StrPath = object

__all__ = [
    "InvalidDistribution",
    "Metadata",
    "metadata_from_distdir",
    "metadata_from_distzip",
    "metadata_from_json",
]


class InvalidDistribution(ValueError):
    """Raised if distribution zipfile is screwed up."""


@dataclass
class Metadata_2_1:
    # NB: API based on packaging.metadata.Metadata (unreleased as of packaging==21.3 but
    # in git)
    name: str
    version: Version
    if sys.version_info >= (3, 10):
        _: dataclasses.KW_ONLY
    summary: Optional[str] = None
    description: Optional[str] = None
    description_content_type: Optional[str] = None
    keywords: Optional[List[str]] = None
    license: Optional[str] = None
    home_page: Optional[str] = None
    download_url: Optional[str] = None
    project_urls: Optional[List[Tuple[str, str]]] = None
    author: Optional[str] = None
    author_email: Optional[str] = None
    maintainer: Optional[str] = None
    maintainer_email: Optional[str] = None
    classifiers: Optional[List[str]] = None

    platforms: Optional[List[str]] = None
    supported_platforms: Optional[List[str]] = None

    requires_python: SpecifierSet = field(default_factory=SpecifierSet)
    requires_dists: Optional[List[Requirement]] = None
    provides_extras: Optional[List[NormalizedName]] = None
    # dynamic_fields: Optional[List[DynamicField]]
    requires_externals: Optional[List[str]] = None

    provides_dists: Optional[List[str]] = None
    obsoletes_dists: Optional[List[str]] = None

    @property
    def display_name(self) -> str:
        return self.name

    @display_name.setter
    def display_name(self, value: str) -> None:
        self.name = value

    @property
    def canonical_name(self) -> NormalizedName:
        return canonicalize_name(self.name)


T = TypeVar("T")


class TypeField(marshmallow.fields.Field, Generic[T]):
    def _deserialize(self, value: Any, *args: Any, **kwargs: Any) -> T:
        T_ = self.__orig_class__.__args__[0]  # type: ignore[attr-defined]
        if isinstance(value, T_):
            return value  # type: ignore[no-any-return]
        try:
            return T_(value)  # type: ignore[no-any-return]
        except ValueError as exc:
            raise marshmallow.ValidationError(str(exc)) from exc


class NormalizedNameField(marshmallow.fields.Field, Generic[T]):
    def _deserialize(self, value: Any, *args: Any, **kwargs: Any) -> NormalizedName:
        return canonicalize_name(value)


class SchemaBase(marshmallow.Schema):
    TYPE_MAPPING = {
        NormalizedName: NormalizedNameField,
        Requirement: TypeField[Requirement],
        SpecifierSet: TypeField[SpecifierSet],
        Version: TypeField[Version],
    }

    class Meta:
        unknown = marshmallow.EXCLUDE


Metadata_2_1_Schema = class_schema(Metadata_2_1, base_schema=SchemaBase)

Metadata = Metadata_2_1


def metadata_from_json(data: Dict[str, Any]) -> Metadata:
    schema = Metadata_2_1_Schema()
    metadata: Metadata_2_1 = schema.load(data)
    return metadata


def metadata_from_distzip(distzip: zipfile.ZipFile) -> Metadata:
    # XXX: Could use zipfile.Path to clean this up in python > 3.8
    for info in distzip.infolist():
        # FIXME: check for multiple METADATA.json?
        if info.filename.endswith("/METADATA.json"):
            json_data = json.loads(distzip.read(info))
            return metadata_from_json(json_data)
    # FIXME: better error if METADATA.json not found
    raise InvalidDistribution("No METADATA.json file found in zip file")


def metadata_from_distdir(dir_path: StrPath) -> Metadata:
    mdfile = Path(dir_path, "METADATA.json")
    try:
        with mdfile.open("rb") as fp:
            json_data = json.load(fp)
    except FileNotFoundError as exc:
        raise InvalidDistribution("No METADATA.json file found in dist") from exc
    return metadata_from_json(json_data)
