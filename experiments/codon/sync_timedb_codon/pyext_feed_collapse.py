"""Legacy filename — do not codon-build this file.

Build the class-free unit instead:

  codon build -release --relocation-model=pic -pyext \\
    -module hpcperfstats_codon_parse -o /out/hpcperfstats_codon_parse \\
    feed_collapse.py

See ``experiments/codon/build_codon_ext_in_pipeline.sh``.
"""
