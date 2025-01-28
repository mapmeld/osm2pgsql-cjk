# osm2pgsql-cjk

Goal: CartoCSS can set alternate CJK fonts for some labels in Taiwan, Hong Kong, and other areas.

Currently OSM uses Noto Sans CJK font for Japan worldwide. This would add a 'cjk' column to the OSM import
process, and then use a script to populate it with an alternate font tag, making it available to Carto / Mapnik.

## Option 1: Spatially unaware

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

More WikiData tags:
- nested P131
- category Q50256 (districts of Hong Kong)
- item Q5895100 (Hong Kong timezone)
- P17 (country)
- category Q706447 (county of Taiwan)
- category Q705296 (district of Taiwan)
- Q712168 (Taiwan timezone)


## Option 2: Bounding Box and Filters

If we set a bounding box / geofence around Hong Kong or Taiwan, we then can add filters to avoid changing the font:
- when there are no Chinese characters
- when names are specifically Simplified Chinese
- when names are specifically Japanese

There are about 161 K nodes in Hong Kong with a `name=*` tag:

```
gis=# select count(*) from planet_osm_point where name is not null;
 count
--------
 160923
```

6.6% of `name=*` tagged nodes use only characters from Latin-1.

```
select count(*) from planet_osm_point WHERE name is not null AND REGEXP_REPLACE(name, '[\x20-\x7E]', '', 'g') != '';
 count
--------
 150276
```

Only 5% of Hong Kong are tagged with Simplified and/or Traditional Chinese names with `name:zh-Hans` and `name:zh-Hant`.
I found only a few cases of `name:zh-Hant-HK=*`.

```
gis=# select count(*) from planet_osm_point WHERE "name:zh-Hans" is not null or "name:zh-Hant" is not null;
 count
-------
  8349
```

There are thousands of nodes where the `name=` value matches the Simplified Chinese.
In about half of these cases, the name does not match the Traditional Chinese. This could be
influenced by how the OpenStreetMap tiles and editor UI display characters, but such specific
tagging could be to reflect real-world naming of the locations.

```
gis=# select count(*) from planet_osm_point WHERE name = "name:zh-Hans"
 count
-------
  4034

gis=# select count(*) from planet_osm_point WHERE name = "name:zh-Hant";
 count
-------
   606

select count(*) from planet_osm_point
  WHERE name = "name:zh-Hans"
  and "name:zh-Hant" is not null
  and name != "name:zh-Hant";
count
-------
 1983
```

At first it seems there are a smaller number of cases with `name` matching `name:zh-Hant`.

```
select count(*) from planet_osm_point
  WHERE name = "name:zh-Hant"
  and "name:zh-Hans" is not null
  and name != "name:zh-Hans";
count
-------
  102
```

Let's check nodes with a bilingual (English / Chinese) label

```
gis=# select name, "name:zh-Hant" from planet_osm_point where name LIKE '%a%' and "name:zh-Hant" is not null limit 5;
                                          name                                           |         name:zh-Hant
-----------------------------------------------------------------------------------------+------------------------------
 新城 E2 區 Zona E2 das Novos Aterros Urbanos                                            | 新城 E2 區
 T18 氹仔客運碼頭公廁 T18 Sanitário público do Terminal Marítimo de Passageiros da Taipa | T18 氹仔客運碼頭
公廁
```

By removing Latin-1 characters and spaces from both sides, we can make it easier to figure out if this
 matches the Simplified or Traditional Chinese name.

```
SELECT
  name,
  "name:zh-Hant",
  REGEXP_REPLACE(name, '[\x20-\x7E]', '', 'g') AS reduced_name,
  REGEXP_REPLACE("name:zh-Hans", '[\x20-\x7E]', '', 'g') AS reduced_hans,
  REGEXP_REPLACE("name:zh-Hant", '[\x20-\x7E]', '', 'g') AS reduced_hant
FROM planet_osm_point
WHERE name != "name:zh-Hant" AND name != "name:zh-Hans"
  AND ("name:zh-Hant" IS NOT NULL or "name:zh-Hans" IS NOT NULL)
  AND REGEXP_REPLACE(name, '[\x20-\x7E]', '', 'g') != ''
  AND (
    REGEXP_REPLACE("name:zh-Hant", '[\x20-\xFF]', '', 'g') != '' OR
    REGEXP_REPLACE("name:zh-Hans", '[\x20-\xFF]', '', 'g') != ''
  )
LIMIT 5;

                                          name                                           |         name:zh-Hant         |         reduced_name         |         reduced_hans         |         reduced_hant
-----------------------------------------------------------------------------------------+------------------------------+------------------------------+------------------------------+------------------------------
 新城 E2 區 Zona E2 das Novos Aterros Urbanos                                            | 新城 E2 區                   | 新城區                       | 新城区                       | 新城區
 T18 氹仔客運碼頭公廁 T18 Sanitário público do Terminal Marítimo de Passageiros da Taipa | T18 氹仔客運碼頭公廁         | 氹仔客運碼頭公廁áúí          | 凼仔客运码头公厕             | 氹仔客運碼頭公廁```
```

The same count match the Simplified Chinese name:

```
SELECT COUNT(*) FROM (
  SELECT REGEXP_REPLACE(name, '[\x20-\x7E]', '', 'g') AS reduced_name
  FROM planet_osm_point
  WHERE REGEXP_REPLACE(name, '[\x20-\x7E]', '', 'g') = REGEXP_REPLACE("name:zh-Hans", '[\x20-\x7E]', '', 'g')
    AND REGEXP_REPLACE(name, '[\x20-\x7E]', '', 'g') != REGEXP_REPLACE("name:zh-Hant", '[\x20-\x7E]', '', 'g')
) AS results;

count
-------
 1983
```

There are more cases using the Traditional Chinese name:

```
SELECT COUNT(*) FROM (
  SELECT REGEXP_REPLACE(name, '[\x20-\x7E]', '', 'g') AS reduced_name
  FROM planet_osm_point
  WHERE REGEXP_REPLACE(name, '[\x20-\x7E]', '', 'g') != REGEXP_REPLACE("name:zh-Hans", '[\x20-\x7E]', '', 'g')
    AND REGEXP_REPLACE(name, '[\x20-\x7E]', '', 'g') = REGEXP_REPLACE("name:zh-Hant", '[\x20-\x7E]', '', 'g')
) AS results;

 count
-------
  2405
```

Sometimes the name is going to match both Simplified and Traditional:

```
SELECT COUNT(*) FROM (
  SELECT REGEXP_REPLACE(name, '[\x20-\x7E]', '', 'g') AS reduced_name
  FROM planet_osm_point
  WHERE REGEXP_REPLACE(name, '[\x20-\x7E]', '', 'g') = REGEXP_REPLACE("name:zh-Hans", '[\x20-\x7E]', '', 'g')
    AND REGEXP_REPLACE(name, '[\x20-\x7E]', '', 'g') = REGEXP_REPLACE("name:zh-Hant", '[\x20-\x7E]', '', 'g')
) AS results;

 count
-------
  1430
```

The broadest query I would apply would be:

```
UPDATE planet_osm_point
SET cjk = 'HK'
WHERE (
  /* geo query and */
  /* has a name */
  name IS NOT NULL AND
  /* name contains characters beyond Latin-1 */
  REGEXP_REPLACE(name, '[\x20-\x7E]', '', 'g') != '' AND
  (
    /* there is no Simplified name */
    "name:zh-Hans" IS NULL
    OR
    /* reduced name matches Traditional (could be matching both) */
    REGEXP_REPLACE(name, '[\x20-\x7E]', '', 'g') = REGEXP_REPLACE("name:zh-Hant", '[\x20-\x7E]', '', 'g')
  )
);
```

This query would affect 146 K nodes (90.6% of Hong Kong)

A narrower query would be:

```
UPDATE planet_osm_point
SET cjk = 'HK'
WHERE (
  /* geo query and */
  /* has a name */
  name IS NOT NULL AND
  /* traditional name was tagged */
  "name:zh-Hant" IS NOT NULL AND
  /* name contains characters beyond Latin-1 */
  REGEXP_REPLACE(name, '[\x20-\x7E]', '', 'g') != '' AND
  /* reduced name matches Traditional (could be matching both) */
  (
    name = "name:zh-Hant"
    OR
    REGEXP_REPLACE(name, '[\x20-\x7E]', '', 'g') = REGEXP_REPLACE("name:zh-Hant", '[\x20-\x7E]', '', 'g')
  )
);
```

This would affect 3.9 K nodes (2.4%);
also 1.5% of roads, and 0.5% of other lines and polygons
