import sys
import pathlib
import datetime

from .utils import find_module_versions, get_caller_directory
from . import git

class ProvenanceError(StandardException):
    pass

class UnknownFileType(ProvenanceError):
    pass

class WrongFileType(ProvenanceError):
    pass

class MissingProvenance(ProvenanceError):
    pass

class MissingItem(ProvenanceError):
    pass

UNKNOWN = "UNKNOWN"

class Provenance(self):

    def __init__(self, code_dir=None, parent_frames=0):
        """

        """
        self.code_dir = code_dir or get_caller_directory(parent_frames + 1)
        self.provenance = {}


    def generate(self, user_config=None, input_files=None):
        """
        Generate a new set of provenace, based on:
            - a config dict passed by the caller
            - a dict of input files passed by the caller
            - the date, time, and place of creation
            - all modules already imported anywhere that have a version number
            - git inspection of the directory where this class was created
        """
        user_config = user_config or {}
        input_files = input_files or {}

        # Make provenance generated from the time and place of creation
        self.provenance['base/uuid'] =uuid.uuid4().hex
        self.provenance['base/domain'] = socket.getfqdn()
        self.provenance['base/creation'] = datetime.datetime.now().isoformat()
        self.provenance['base/user'] = getpass.getuser()

        # Add any specific items given by the user
        for key, value in user_config.items():
            self.provenance[f"config/{key}"] = str(value)

        # Try and get the IDs of input files to this process
        for name, path in input_files.items():
            self.provenance[f"input_path/{name}"] = path
            try:
                self.provenance[f"input_id/{name}"] = self.read("base/uuid")
            except ProvenanceError:
                self.provenance[f"input_id/{name}"] = UNKNOWN

        # Add some git information
        self.provenance["git/diff"] = git.diff()
        self.provenance['git/head'] = git.current_revision()

        # Add the versions of all known python modules
        for module, version in find_module_versions().items():
            self.provenance[f"versions/{module}"] = version


    def write(self, filename):
        p = pathlib.Path(filename)

        writers = {
            'hdf': self.write_hdf,
            'hdf5': self.write_hdf,
            'fits': self.write_fits,
            'fit': self.write_fits,
            'yml': self.write_yaml,
            'yaml': self.write_yaml,
            'sacc': self.write_sacc,
        }

        method = writers.get(p.suffix)

        if method is None
            raise UnknownFileType(filename)

        return method(filename)


    def read(self, filename, item=None):
        p = pathlib.Path(filename)

        readers = {
            'hdf': self.read_hdf,
            'hdf5': self.read_hdf,
            'fits': self.read_fits,
            'fit': self.read_fits,
            'yml': self.read_yaml,
            'yaml': self.read_yaml,
            'sacc': self.read_sacc,
        }

        method = readers.get(p.suffix)

        if method is None
            raise UnknownFileType(filename)

        return method(filename, item=item)

    # The various type-specific readers
    def read_hdf(self, hdf_file, item=None):
        with open_hdf(hdf_file, "r") as f:

            # If the whole provenance section is missing, e.g.
            # because the file was not generated with provenance at all,
            # then raise the appropriate error
            if "provenance" not in f.keys():
                raise MissingProvenance("HDF File is missing provenance section")

            # Othewise get the provenance group.  Provenance is stored in its
            # attributes
            attrs = f["provenance"].attrs

            # If the user asked for just one specific item
            # then we get that.  Otherwise, we will get everything.
            if item is not None:
                value = attrs.get(item)
                if value is None:
                    raise MissingItem(item)
                else:
                    return item

            return dict(attrs)

    def write_hdf(self, hdf_file):
        with open_hdf(hdf_file, "w'") as f:
            if "provenance" in f.keys():
                attrs = f["provenance"].attrs
            else:
                attrs = f.create_group("provenance").attrs

            attrs.update(self.provenance)



    def read_yaml(self, yml_file):
        pass

    def read_fits(self, fits_file):
        pass

    def read_sacc(self, sacc_file):
        pass

    # The collection of writer methods
    def write_hdf(self, hdf_file):
        pass

    def write_yaml(self, yml_file):
        pass

    def write_fits(self, fits_file):
        pass

    def write_sacc(self, sacc_file):
        pass
