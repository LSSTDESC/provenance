A Prototype DESC Provenance Library
===================================

Simple Usage
------------

The core usage of this provenance is:

```
from desc_provenance import Provenance

p = Provenance()
p.generate()
p.write(output_filename)
```
where `output_filename` is the name of an output that you *already* saved earlier in the code.

The system will have recorded in that file:
- A unique ID for this process
- A unique ID for the file
- The domain name where it was generated
- The date and time it was run
- The name of the user who ran it
- The command line argument used
- The git revision and diff information for the directory where the code is



Recording More Provenance
-------------------------

We should also record:
- configuration parameters that we used in this run
- input files we read earlier
- any comments we have

We can do that by first collecting any config parameters we were passed
and the paths to all our input files:
```
code_config = { "nbin": 100, "classifier": "flexzboost", "target": 0.2}
input_files = {"catalog": "./my_input.hdf5"}
comments = [
	"Replaces version 14a",
	"Should fix convergence error"
]
```

Now we can generaete a provenance object that includes these
```
p = Provenance()
p.generate(code_config, input_files, comments)
```

This will contain, in addition to the provenance above:
- The specific configuration we passed in
- The paths and, if they have one, the unique IDs for each of the input files.
- our comments

File types
----------

This library currently works with FITS, YAML, and HDF5 files.

Saving to open files
--------------------

We can also write provenance to a file we have opened and not yet closed,
instead of closing it first:
```
output_filename = "my_output.hdf5"
f = h5py.File(output_filename, "w")
# ...
p.write(f)
# ...
f.close()
```
