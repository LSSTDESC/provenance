import tempfile
from desc_provenance import Provenance, __version__ as lib_version, errors, utils
from pprint import pprint
import pytest
import datetime
import os


def test_generate():
    p = Provenance()

    # Check that the basic provenance information is generated correctly.
    # temporarily change the user name so that we check it's okay
    logname = os.environ.get("LOGNAME")
    os.environ["LOGNAME"] = "mr_potato"
    user_config = {
        "xxx": "abc",
        "car": "47",
    }

    try:
        p.generate(
            user_config,
        )
    finally:
        if logname is None:
            del os.environ["LOGNAME"]
        else:
            os.environ["LOGNAME"] = logname

    assert p["base", "user"] == "mr_potato"

    # check our own version is correct, and that of pytest
    assert p["versions", "desc_provenance"] == lib_version
    assert p["versions", "pytest"] == pytest.__version__

    # check some basic information
    # date and time should be in the last few moments
    dt = datetime.datetime.now() - datetime.datetime.fromisoformat(
        p["base", "creation"]
    )
    assert dt.total_seconds() < 5


def test_inputs():
    p = Provenance()
    p.generate()
    with tempfile.TemporaryDirectory() as dirname:
        file_id = p.write("test1.hdf")

        q = Provenance()
        input_files = {"tag1": "./test1.hdf", "tag2": "./non_existent_file.hdf"}
        q.generate(input_files=input_files)

        assert file_id == q["input_id", "tag1"]
        assert "UNKNOWN" == q["input_id", "tag2"]


@pytest.mark.parametrize(
    "file_type, opener", [("hdf", utils.open_hdf), ("yml", utils.open_file)]
)
def test_new(file_type, opener):
    p = Provenance()
    p["sec", "aaa"] = "xxx"
    p["sec", "bbb"] = 123
    p["sec", "ccc"] = 3.14
    p["sec", "ddd"] = "cat"
    p["sec", "eee"] = 4.14

    with tempfile.TemporaryDirectory() as dirname:
        fname = os.path.join(dirname, f"test.{file_type}")
        file_id = p.write(fname)

        assert os.path.exists(fname)

        q = Provenance()
        q.read(fname)

        print(q.provenance)
        assert q["sec", "aaa"] == "xxx"
        assert q["sec", "bbb"] == 123
        assert q["sec", "ccc"] == 3.14

        # check the direct getter class methods work
        assert Provenance.get(fname, "sec", "ddd") == "cat"
        assert Provenance.get(fname, "sec", "eee") == 4.14

        # the file ID will not be in the original as it changes
        #  but we saved it
        print(q.provenance)
        assert q["base", "file_id"] == file_id
        del q["base", "file_id"]
        assert p.provenance == q.provenance


def test_new_fits():
    file_type = "fits"
    p = Provenance()
    p["sec", "aaa"] = "xxx"
    p["sec", "bbb"] = 123
    p["sec", "ccc"] = 3.14
    p["sec", "DDD"] = "cat"
    p["sec", "eee"] = 4.14

    with tempfile.TemporaryDirectory() as dirname:
        fname = os.path.join(dirname, f"test.{file_type}")

        #  Write to now-closed
        file_id = p.write(fname)

        assert os.path.exists(fname)

        q = Provenance()
        q.read(fname)

        assert q["sec", "aaa"] == "xxx"
        assert q["sec", "bbb"] == 123
        assert q["sec", "ccc"] == 3.14

        # check the direct getters work
        assert q.get(fname, "sec", "DDD") == "cat"
        assert q.get(fname, "sec", "eee") == 4.14

        assert file_id == q["base", "file_id"]
        del q["base", "file_id"]
        assert p.provenance == q.provenance


def test_fits_multiline():
    file_type = "fits"
    p = Provenance()
    p["sec", "aaa"] = "Two households;\nboth alike in dignity!"

    with tempfile.TemporaryDirectory() as dirname:
        fname = os.path.join(dirname, f"test.{file_type}")

        #  Write to now-closed
        p.write(fname)

        assert os.path.exists(fname)

        q = Provenance()
        q.read(fname)

        assert p["sec", "aaa"] == q["sec", "aaa"]


def test_existing_hdf():
    import h5py

    p = Provenance()
    p["sec", "aaa"] = "xxx"
    p["sec", "bbb"] = 123
    p["sec", "ccc"] = 3.14
    p["sec", "DDD"] = "cat"
    p["sec", "eee"] = 4.14

    with tempfile.TemporaryDirectory() as dirname:
        fname = os.path.join(dirname, "test.hdf")
        fname2 = os.path.join(dirname, "test2.hdf")

        with utils.open_hdf(fname, "w") as f:
            f.create_group("cake")

        id1 = p.write(fname)
        id2 = p.write(fname2)

        assert id1 != id2

        q1 = Provenance()
        q1.read(fname)
        q2 = Provenance()
        q2.read(fname2)

        assert q1["base", "file_id"] == id1
        assert q2["base", "file_id"] == id2

        # Check full round trip
        q1.provenance.pop(("base", "file_id"))
        q2.provenance.pop(("base", "file_id"))
        assert q1.provenance == q1.provenance


def test_yml():
    import ruamel.yaml as yaml

    y = yaml.YAML()
    # check nothing is overridden
    d = {
        "cat": "good",
        "dog": "bad",
        "spoon": 45.6,
        "cow": -222,
    }
    with tempfile.TemporaryDirectory() as dirname:
        fname = os.path.join(dirname, "test.yml")
        y.dump(d, open(fname, "w"))

        p = Provenance()
        p.generate()
        file_id = p.write(fname)

        #  check prov reads
        q = Provenance()
        q.read(fname)

        assert q["base", "file_id"] == file_id
        assert q["base", "process_id"] == q["base", "process_id"]

        d2 = y.load(open(fname))
        d2.pop("provenance")
        assert d == d2

        q = Provenance()
        q.read_yaml(open(fname))
        assert q["base", "file_id"] == file_id
        assert q["base", "process_id"] == q["base", "process_id"]


def test_write_fails():
    p = Provenance()
    p.generate()
    with pytest.raises(errors.ProvenanceFileTypeUnknown):
        p.write("test.xyz")


if __name__ == "__main__":
    test_yml()
