# Data access and redistribution

The public release intentionally does **not** redistribute the underlying daily market-price panel or copies of third-party index-composition documents.

The analysis retrieves adjusted daily prices from Yahoo Finance through `yfinance`. Yahoo Finance states that information displayed on or provided by Yahoo Finance must not be redistributed. Users should retrieve the data from the original provider under its current terms when reproducing the analysis.

Official BMV/MexDer composition notices and the S&P/BMV IPC constituent export used during the research are also not bundled here. The public notebook fixes the 38-name candidate panel described in the manuscript and does not require copies of those documents for the core network results.

For provenance, `../provenance/source_checksums.csv` records cryptographic checksums of the exact local source files used by the authors without redistributing their contents. The checksum of the local market-price snapshot lets an authorized user verify that they hold the same input file.
