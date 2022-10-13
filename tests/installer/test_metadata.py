import json
from pathlib import Path
from typing import Any
from typing import Dict
from zipfile import ZipFile

import marshmallow
import pytest
from packaging.requirements import Requirement
from packaging.version import Version

from barnhunt.installer.metadata import InvalidDistribution
from barnhunt.installer.metadata import Metadata
from barnhunt.installer.metadata import metadata_from_distdir
from barnhunt.installer.metadata import metadata_from_distzip
from barnhunt.installer.metadata import metadata_from_json


def test_Metadata_display_name() -> None:
    md = Metadata("foo", Version("1.0"))
    assert md.display_name == "foo"
    md.display_name = "foo.bar"
    assert md.display_name == "foo.bar"


def test_Metadata_canonical_name() -> None:
    md = Metadata("foo.bar", Version("1.0"))
    assert md.canonical_name == "foo-bar"


def test_metadata_from_json_requires_dist() -> None:
    md = metadata_from_json(
        {
            "name": "name",
            "version": "1.0",
            "requires_dists": ["barnhunt>1.1", Requirement("lxml")],
        }
    )
    requires_dists = md.requires_dists
    assert isinstance(requires_dists, list)
    assert [req.name for req in requires_dists] == ["barnhunt", "lxml"]


def test_metadata_from_json_bad_requires_dist() -> None:
    with pytest.raises(marshmallow.ValidationError):
        metadata_from_json(
            {"name": "name", "version": "1.0", "requires_dists": ["bad requirement"]}
        )


def test_metadata_from_json_requires_python() -> None:
    md = metadata_from_json(
        {"name": "name", "version": "1.0", "requires_python": ">3.7"}
    )
    assert Version("3.8") in md.requires_python
    assert Version("3.7") not in md.requires_python


def test_metadata_from_json_provides_extras() -> None:
    md = metadata_from_json(
        {"name": "name", "version": "1.0", "provides_extras": ["foo_bar"]}
    )
    assert md.provides_extras == ["foo-bar"]


@pytest.fixture
def json_data() -> Dict[str, Any]:
    return {
        "name": "test.name",
        "version": "0.42",
    }


def test_metadata_from_zipdist(tmp_path: Path, json_data: Dict[str, Any]) -> None:
    zip_path = tmp_path / "test.zip"
    with ZipFile(zip_path, "w") as zf:
        zf.writestr("org.dairiki.foo_bar/METADATA.json", json.dumps(json_data))
    with ZipFile(zip_path) as zf:
        md = metadata_from_distzip(zf)
    assert md.name == json_data["name"]


def test_metadata_from_zipdist_invalid(tmp_path: Path) -> None:
    zip_path = tmp_path / "test.zip"
    with ZipFile(zip_path, "w") as zf:
        zf.writestr("org.dairiki.foo_bar/foo.txt", "howdy")
    with ZipFile(zip_path) as zf:
        with pytest.raises(InvalidDistribution):
            metadata_from_distzip(zf)


def test_metadata_from_zipdir(tmp_path: Path, json_data: Dict[str, Any]) -> None:
    dist_path = tmp_path / "test.dist"
    dist_path.mkdir()
    Path(dist_path, "METADATA.json").write_text(json.dumps(json_data))

    md = metadata_from_distdir(dist_path)
    assert md.name == json_data["name"]


def test_metadata_from_zipdir_invalid(tmp_path: Path) -> None:
    dist_path = tmp_path / "test.dist"
    dist_path.mkdir()
    Path(dist_path, "foo.text").write_text("bar")

    with pytest.raises(InvalidDistribution):
        metadata_from_distdir(dist_path)
