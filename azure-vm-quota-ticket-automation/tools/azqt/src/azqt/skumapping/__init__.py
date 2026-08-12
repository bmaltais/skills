"""Static VM SKU / informal-size -> Compute_Quota_Family mapping for azqt.

``table.json`` is the deterministic mapping table (Req 2.5); ``resolver.py``
implements the exact-SKU and informal-size lookup rules used by the
``map-sku`` subcommand (task 5) on top of it.
"""
