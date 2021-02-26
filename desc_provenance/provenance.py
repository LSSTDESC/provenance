from . import git
from . import errors
from . import utils
import sys
import uuid
import socket
import getpass
import pathlib
import warnings
import datetime
import functools
import contextlib
import collections

# Some useful constants
unknown_value = "UNKNOWN"
provenance_group = "provenance"
base_section = "base"
config_section = "config"
input_id_section = "input_id"
input_path_section = "input_path"
git_section = "git"
versions_section = "versions"


def writer_method(method):
    """Do some book-keeping to turn a provenance method into a writer method

    We put this decorator around all the methods that write
    provenance to a file, so that they all generate, remove,
    and return a unique ID for each new file they write to.

    It's not intended for users.
    """
    # This makes the decorator "well-behaved" so that it
    #  doesn't change the name of the function when printed,
    # etc.
    @functools.wraps(method)
    def wrapped_method(self, *args, **kwargs):
        #  Make a new UUID for this file
        file_id = uuid.uuid4().hex
        #  Record it in the provenance object
        self[base_section, "file_id"] = file_id

        # I was a bit confused at the need to include
        # self here, but it seems to be required
        try:
            method(self, *args, **kwargs)
        finally:
            # At the end, remove it from the Provenance, because it will not
            # be relevant for future files
            del self.provenance[base_section, "file_id"]
        #  But return it; this is mainly to help testing
        return file_id

    return wrapped_method


class Provenance:
    """Collects, generates, reads, and writes provenance information.

    This object can be used like a dictionary with two keys:
    provenance[category, key] = value
    """

    def __init__(self, code_dir=None, parent_frames=0):
        """Create an empty provenance object"""
        self.code_dir = code_dir or utils.get_caller_directory(parent_frames + 1)
        self.provenance = {}

    # Generation methods
    # ------------------
    def generate(self, user_config=None, input_files=None):
        """
        Generate a new set of provenance, containing:
            - the date, time, and place of creation
            - the user and domain name
            - all python modules already imported anywhere that have a version number
            - git info about the directory where this instance was created
            - sys.argv
            - a config dict passed by the caller
            - a dict of input files passed by the caller
        """
        # Record various core pieces of information
        self._add_core_info()
        self._add_git_info()
        self._add_module_versions()
        self._add_argv_info()

        #  Add user inputs
        if input_files is not None:
            for name, path in input_files.items():
                self.add_input_file(name, path)

        #  Add any specific items given by the user
        if user_config is not None:
            for key, value in user_config.items():
                self[config_section, key] = value

    #  Core methods called in generate above
    # -------------------------------------
    def _add_core_info(self):
        self[base_section, "process_id"] = uuid.uuid4().hex
        self[base_section, "domain"] = socket.getfqdn()
        self[base_section, "creation"] = datetime.datetime.now().isoformat()
        self[base_section, "user"] = getpass.getuser()

    def _add_argv_info(self):
        for i, arg in enumerate(sys.argv):
            self[base_section, f"argv_{i}"] = arg

    def _add_git_info(self):
        #  Add some git information
        self[git_section, "diff"] = git.diff()
        self[git_section, "head"] = git.current_revision()

    def _add_module_versions(self):
        for module, version in utils.find_module_versions().items():
            self[versions_section, module] = version

    def add_input_file(self, name, path):
        """
        Tell the provenance the name and path to one of your input files
        so it can be recorded correctly in the output.

        Parameters
        ----------
        name: str
            A tag or name representing the file

        path: str or pathlib.Path
            The path to the file
        """
        # get the absolute form path to the file
        path = str(pathlib.Path(path).absolute().resolve())

        # Save it in ourselves
        self[input_path_section, name] = path
        # If the file was saved with its own provenance then it will have its own
        #  unique file_id.  Try to record that ID.  The file may be some other type,
        # or not have provenance, so ignore any errors here.
        try:
            self[input_id_section, name] = self.get(path, base_section, "file_id")
        except errors.ProvenanceError:
            self[input_id_section, name] = unknown_value

    # Dictionary methods
    # ------------------
    def __getitem__(self, section_name):
        section, name = section_name
        return self.provenance[section, name]

    def __setitem__(self, section_name, value):
        section, name = section_name
        self.provenance[section, name] = value

    def __delitem__(self, section_name):
        section, name = section_name
        del self.provenance[section, name]

    def update(self, d):
        """
        Update the provenance from a dictionary.

        The dictionary keys should be tuples of (category, key).
        The values can be any basic type.

        Parameters
        ----------
        d: dict or mapping
            The dict to update from.
        """
        for (section, name), value in d.items():
            self.provenance[section, name] = value

    #  Generic I/O Methods
    # -----------
    def write(self, filename):
        """
        Write provenance to a named file, guessing the file type from its suffix.

        Use the various write_* methods intead to write to a file you have already
        opened, or if the file suffix does not match the type.

        Parameters
        ----------
        filename: str
        """
        p = pathlib.Path(filename)

        writers = {
            ".hdf": self.write_hdf,
            ".hdf5": self.write_hdf,
            ".fits": self.write_fits,
            ".fit": self.write_fits,
            ".yml": self.write_yaml,
            ".yaml": self.write_yaml,
            ".sacc": self.write_sacc,
        }

        method = writers.get(p.suffix)

        if method is None:
            raise errors.ProvenanceFileTypeUnknown(filename)

        return method(filename)

    def read(self, filename):
        """
        Read all provenance from any supported file type, guessing
        the file type from its suffix.

        If the suffix does not match the type you can use one of the specific read_
        methods instead.  You can also pass open file objects directly to those methods.

        Parameters
        ----------
        filename: str

        Returns
        -------
        None
        """
        p = pathlib.Path(filename)

        readers = {
            ".hdf": self.read_hdf,
            ".hdf5": self.read_hdf,
            ".fits": self.read_fits,
            ".fit": self.read_fits,
            ".yml": self.read_yaml,
            ".yaml": self.read_yaml,
            ".sacc": self.read_sacc,
        }

        method = readers.get(p.suffix)
        if method is None:
            raise errors.ProvenanceFileTypeUnknown(filename)

        return method(filename)

    @classmethod
    def get(cls, filename, section, key):
        """
        Get a single item of provenance from any supported file type, guessing
        the file type from its suffix.

        If the suffix does not match the type you can use one of the specific get_
        methods instead.  You can also pass open file objects directly to those methods.

        Parameters
        ----------
        filename: str
        """

        p = pathlib.Path(filename)
        if not p.exists():
            raise errors.ProvenanceMissingFile(filename)

        getters = {
            ".hdf": cls.get_hdf,
            ".hdf5": cls.get_hdf,
            ".fits": cls.get_fits,
            ".fit": cls.get_fits,
            ".yml": cls.get_yaml,
            ".yaml": cls.get_yaml,
            ".sacc": cls.get_sacc,
        }

        method = getters.get(p.suffix)
        if method is None:
            raise errors.ProvenanceFileTypeUnknown(filename)

        return method(filename, section, key)

    # HDF Methods
    # -----------
    @classmethod
    def _read_get_hdf(cls, hdf_file, item=None):
        with utils.open_hdf(hdf_file, "r") as f:
            # If the whole provenance section is missing, e.g.
            #  because the file was not generated with provenance at all,
            # then raise the appropriate error
            if provenance_group not in f.keys():
                raise errors.ProvenanceMissingSection(
                    "HDF File is missing provenance section"
                )

            # Othewise get the provenance group.  Provenance is stored in its
            #  attributes of subgroups
            g = f[provenance_group]

            # If we are being called from read_hdf then we want to read everything
            if item is None:
                d = {}
                # Go to all the (category) subgroups
                for section in g.keys():
                    sg = g[section]
                    # and read all the attributes in each one
                    for key, val in sg.attrs.items():
                        d[section, key] = val
                return d
            # Otherwise just read the one requested item
            else:
                section, key = item
                if section not in g.keys():
                    raise errors.ProvenanceMissingItem(f"{section}/{key}")

                # Will be None if not present
                value = g[section].attrs.get(key)

                if value is None:
                    raise errors.ProvenanceMissingItem(item)
                else:
                    return value

    @classmethod
    def get_hdf(cls, hdf_file, section, key):
        """Get a single item of provenance from an HDF file.

        Parameters
        ----------
        hdf_file: str or h5py.File
            The file name or an open file

        section: str
            The provenance item category

        key: str
            The provenance item name

        Returns
        -------
        value
            The value (of any type) found in the file
        """
        return cls._read_get_hdf(hdf_file, (section, key))

    def read_hdf(self, hdf_file):
        """Read provenance from an HDF5 file.

        Parameters
        ----------
        hdf_file: str or h5py.File.FITS
            The file name or an open file object
        """
        d = self._read_get_hdf(hdf_file)
        self.update(d)

    @writer_method
    def write_hdf(self, hdf_file):
        """Write provenance to an HDF5 file.

        Parameters
        ----------
        hdf_file: str or h5py.File
            The file name or an open file object
        """
        with utils.open_hdf(hdf_file, "a") as f:
            #  Group may or may not exist already
            if provenance_group in f.keys():
                g = f[provenance_group]
            else:
                g = f.create_group(provenance_group)

            # Write each category to a subgroup
            for (section, key), value in self.provenance.items():
                # Create subgroup if it does not exist already
                if section not in g.keys():
                    subg = g.create_group(section)
                else:
                    subg = g[section]

                # Write values to subgroup attributes
                subg.attrs[key] = value

    # FITS Methods
    # ------------
    @classmethod
    def get_fits(cls, fits_file, section, key):
        """Get a single item of provenance from a FITS file.

        Parameters
        ----------
        fits_file: str or fitsio.FITS
            The file name or an open file

        section: str
            The provenance item category

        key: str
            The provenance item name

        Returns
        -------
        value
            The value (of any type) found in the file
        """
        return cls._read_get_fits(fits_file, (section, key))

    def read_fits(self, fits_file):
        """Read proveance from a FITS file.

        Loads all the provenance found in a FITS file.

        Parameters
        ----------
        fits_file: str or fitsio.FITS
            The file name or an open file object

        """
        d = self._read_get_fits(fits_file)
        self.update(d)

    @writer_method
    def write_fits(self, fits_file):
        """Write provenance to a FITS file.

        Parameters
        ----------
        fits_file: str or fitsio.FITS
            The file name or an open file object
        """
        with utils.open_fits(fits_file, "rw") as f:

            #  Create the group if it doesn't exist
            if provenance_group in f:
                ext = f[provenance_group]
            else:
                f.create_image_hdu(extname=provenance_group)
                f.update_hdu_list()
                ext = f[provenance_group]

            #  Helper local function to write a key.
            # To maintain case we store items as a trio
            #  of keys specifying category, key, and value
            def write_key(s, k, v, i):
                ext.write_key(f"sec_{i}", s)
                ext.write_key(f"key_{i}", k)
                ext.write_key(f"val_{i}", v)

            # Write the keys we have one by one
            for i, ((section, key), value) in enumerate(self.provenance.items()):
                # FITS header items can't contain newlines, so we break up
                #  any text with newlines into separate entries which we patch
                # together again when loading
                if isinstance(value, str) and "\n" in value:
                    values = value.split("\n")
                    for j, v in enumerate(values):
                        write_key(section, key, v, f"{i}_{j}")
                # or if it's any other item we just put it in directly
                else:
                    write_key(section, key, value, i)

    # Internal method implementing the read and get methods
    @classmethod
    def _read_get_fits(cls, fits_file, item=None):
        with utils.open_fits(fits_file, "r") as f:
            ext = f[0]
            # We may be called from the get or read methods.
            # In the former case we will be given a specific item
            # to get, which we split here
            if item is not None:
                target_sec, target_key = item

            #  Read the entire header. A bit wasteful if we only want a single
            #  item from it, but this shouldn't be a performance bottleneck.
            hdr = ext.read_header()

            # We have recorded items in trios of KEY_0, SEC_0, VAL_0, _1, _2 etc.
            # so count how many keys we have
            indices = [k[4:] for k in hdr if k.upper().startswith("KEY_")]

            #  We will collect the number of lines for each multi-line
            #  item, so we can patch together later.
            multiline_indices = collections.defaultdict(int)
            d = {}

            # split these keys into multi-line and normal keys
            for index in indices:
                if "_" in index:
                    orig_index, _ = index.split("_", 1)
                    multiline_indices[orig_index] += 1
                else:
                    #  Handle the normal keys just by reading them
                    sec = hdr[f"SEC_{index}"]
                    val = hdr[f"VAL_{index}"]
                    key = hdr[f"KEY_{index}"]
                    #  If this is called from get_ then return
                    # if we have found the desired object
                    if item is not None:
                        if (sec == target_sec) and (key == target_key):
                            return val
                    #  Otherwise just build up all the items
                    else:
                        d[sec, key] = val

            #  Now deal with all the multiline ones we found.
            #  we recorded the number of entries for each of them
            for index, n in multiline_indices.items():
                vals = []
                # sec and key should be the same for them all
                sec = hdr[f"SEC_{index}_0"]
                key = hdr[f"key_{index}_0"]

                # reassemble into a multi-line text
                for i in range(n):
                    vals.append(hdr[f"VAL_{index}_{i}"])
                val = "\n".join(vals)

                # Check if the target is this multiline item
                if item is not None:
                    if (sec == target_sec) and (key == target_key):
                        return val
                else:
                    d[sec, key] = val

            # If we were not asked for a specific item then return
            # the entire thing
            if item is None:
                return d
            else:
                # If we were asked for an item then if we've got this far
                #  then we've failed.
                raise errors.ProvenanceMissingItem(
                    f"Missing item {target_sec} {target_key}"
                )

    # Other I/O Methods
    # -----------------

    def read_yaml(self, yml_file):
        raise NotImplementedError("File type note implemented")

    @classmethod
    def get_yaml(self, yml_file, item):
        raise NotImplementedError("File type note implemented")

    @writer_method
    def write_yaml(self, yml_file):
        raise NotImplementedError("File type note implemented")

    @classmethod
    def get_sacc(self, sacc_file):
        raise NotImplementedError("File type note implemented")

    def read_sacc(self, sacc_file):
        raise NotImplementedError("File type note implemented")

    @writer_method
    def write_sacc(self, sacc_file):
        raise NotImplementedError("File type note implemented")
