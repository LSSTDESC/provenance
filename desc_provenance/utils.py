import distutils.version
import sys
import inspect
import pathlib
import collections

def get_caller_directory(parent_frames=0):
    """
    Find the directory where the code calling this
    module lives, or where the code calling
    that code lives if grandparent=True.
    """
    previous_frame = inspect.currentframe().f_back
    # go back more frames if desired
    for i in range(parent_frames):
        previous_frame = previous_frame.f_back

    filename = inspect.getframeinfo(previous_frame).filename
    p = pathlib.Path(filename)
    if not p.exists():
        # dynamically generated or interactive mode
        return None
    return str(p.parent)



def find_module_versions():
    """
    Generate a dictionary of versions of all imported modules
    by looking for __version__ or version attributes on them.
    """
    versions = {}
    for name, module in sys.modules.items(): 
        if hasattr(module, 'version'): 
            v = module.version 
        elif hasattr(module, '__version__'): 
            v = module.__version__ 
        else:
            continue
        if isinstance(v, str) or isinstance(v, distutils.version.Version):
            versions[name] = str(v)
    return versions

@collections.contextlib
def open_hdf(hdf_file, mode):
    import h5py
    if isinstance(hdf_file, str):
        try:
            f = h5py.File(hdf_file, mode)
            yield f
        finally:
            f.close()
    else:
        yield hdf_file
