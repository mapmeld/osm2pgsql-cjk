# osm2pgsql-cjk

Goal: CartoCSS can set alternate CJK fonts for some labels in Taiwan, Hong Kong, and other areas.

Currently OSM uses Noto Sans CJK font for Japan worldwide. This would add a 'cjk' column to the OSM import
process, and then use a script to populate it with an alternate font tag, making it available to Carto / Mapnik.

We want to know that a label is in Taiwan or Hong Kong without using a bounding box or adding new tags

Current method:
- common practices in geodata: use of `is_in:zh=台灣...`
- use a WikiData query to identify cities, towns, and landmarks in the region

The current script finds hundreds of locations:

```
INFO:root:Starting load of WikiData CJK information into database
INFO:root:Searching for is_in:zh tags starting with one of ['台灣', '臺灣']
INFO:root:Updated 469 points
INFO:root:Updated 25 roads
INFO:root:Updated 25 other lines
INFO:root:Updated 35 polygons
INFO:root:Querying WikiData for OSM data within Taiwan
INFO:root:Found 9 places in WikiData
INFO:root:WikiData returned 0 nodes
INFO:root:WikiData returned 9 ways and 0 relations
INFO:root:Updated 38 roads
INFO:root:Updated 240 other lines
INFO:root:Updated 8 polygons]

INFO:root:Querying WikiData for OSM data within Hong Kong
INFO:root:Found 422 places in WikiData
INFO:root:WikiData returned 169 nodes
INFO:root:Updated 165 points
INFO:root:WikiData returned 152 ways and 102 relations
INFO:root:Updated 359 roads
INFO:root:Updated 1019 other lines
INFO:root:Updated 169 polygons
```
