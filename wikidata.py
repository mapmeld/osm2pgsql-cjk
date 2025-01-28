#!/usr/bin/env python3
# Script fills a 'cjk' column in the database if WikiData labels they are in Hong Kong or Taiwan
# This addresses an issue with Han unification, where the same codepoint can have a different appearance
# in mainland China, Japan, Korea, Hong Kong, and Taiwan.
# CartoCSS can then use the 'cjk' column to set the correct font.

# uses same database args as get-external-data.py

import argparse, logging, yaml
from time import sleep
import psycopg2
from SPARQLWrapper import SPARQLWrapper, JSON

places = [
    { 'id': 'Q865', 'font': 'TC', 'name': 'Taiwan', 'is_in:zh': ['台灣', '臺灣'] },
    { 'id': 'Q8646', 'font': 'HK', 'name': 'Hong Kong' },
]

def queryPlace(place):
    sparql = SPARQLWrapper("https://query.wikidata.org/sparql")

    query = """
    SELECT ?item ?itemLabel ?osmid ?osmway ?osmrelation WHERE {
    # item administratively within PLACE
    ?item wdt:P131 wd:PLACE.

    # Match items with at least one of the OpenStreetMap-related properties
    OPTIONAL { ?item wdt:P11693 ?osmid. }       # OpenStreetMap node ID
    OPTIONAL { ?item wdt:P402 ?osmway. }        # OpenStreetMap identifier
    OPTIONAL { ?item wdt:P10689 ?osmrelation. } # OpenStreetMap relation ID
    FILTER(BOUND(?osmid) || BOUND(?osmrelation) || BOUND(?osmway))

    # Including name
    SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
    }
    """

    logging.info(f"Querying WikiData for OSM data within {place['name']}")
    sparql.setQuery(query.replace('PLACE', place['id']))
    sparql.setReturnFormat(JSON)

    results = sparql.query().convert()
    return results["results"]["bindings"]


def main():
    # parse options
    parser = argparse.ArgumentParser(
        description="Load CJK script information from WikiData into a database")

    parser.add_argument("-c", "--config", action="store", default="external-data.yml",
                        help="Name of configuration file (default external-data.yml)")

    parser.add_argument("-d", "--database", action="store",
                        help="Override database name to connect to")
    parser.add_argument("-H", "--host", action="store",
                        help="Override database server host or socket directory")
    parser.add_argument("-p", "--port", action="store",
                        help="Override database server port")
    parser.add_argument("-U", "--username", action="store",
                        help="Override database user name")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Be more verbose. Overrides -q")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Only report serious problems")
    parser.add_argument("-w", "--password", action="store",
                        help="Override database password")

    opts = parser.parse_args()

    if opts.verbose:
        logging.basicConfig(level=logging.DEBUG)
    elif opts.quiet:
        logging.basicConfig(level=logging.WARNING)
    else:
        logging.basicConfig(level=logging.INFO)

    logging.info("Starting load of WikiData CJK information into database")

    with open(opts.config) as config_file:
        config = yaml.safe_load(config_file)
        database = opts.database or config["settings"].get("database")
        host = opts.host or config["settings"].get("host")
        port = opts.port or config["settings"].get("port")
        user = opts.username or config["settings"].get("username")
        password = opts.password or config["settings"].get("password")

        conn = psycopg2.connect(database=database,
                        host=host, port=port,
                        user=user,
                        password=password)
        conn.set_client_encoding('UTF8')
        cursor = conn.cursor()

        for place in places:
            if "is_in:zh" in place:
                logging.info(f"Searching for is_in:zh tags starting with one of {place['is_in:zh']}")

                placeholders = ', '.join("%s" for _ in place['is_in:zh'])

                query = f"UPDATE planet_osm_point SET cjk = %s WHERE SUBSTR(\"is_in:zh\", 1, 2) IN ({placeholders})"
                cursor.execute(query, [place['font'], *place['is_in:zh']])
                rows_affected = cursor.rowcount
                logging.info(f"Updated {rows_affected} points")

                query = f"UPDATE planet_osm_roads SET cjk = %s WHERE SUBSTR(\"is_in:zh\", 1, 2) IN ({placeholders})"
                cursor.execute(query, [place['font'], *place['is_in:zh']])
                rows_affected = cursor.rowcount
                logging.info(f"Updated {rows_affected} roads")
                query = f"UPDATE planet_osm_line SET cjk = %s WHERE SUBSTR(\"is_in:zh\", 1, 2) IN ({placeholders})"
                cursor.execute(query, [place['font'], *place['is_in:zh']])
                rows_affected = cursor.rowcount
                logging.info(f"Updated {rows_affected} other lines")
                query = f"UPDATE planet_osm_polygon SET cjk = %s WHERE SUBSTR(\"is_in:zh\", 1, 2) IN ({placeholders})"
                cursor.execute(query, [place['font'], *place['is_in:zh']])
                rows_affected = cursor.rowcount
                logging.info(f"Updated {rows_affected} polygons")

            results = queryPlace(place)
            logging.info(f'Found {len(results)} places in WikiData')

            nodes = []
            ways = []
            relations = []
            for result in results:
                # extract usable WikiData ID
                wikidataID = result["item"]["value"].split('/')[-1]
                if "osmid" in result:
                    nodes.append(wikidataID)
                if "osmway" in result:
                    ways.append(wikidataID)
                if "osmrelation" in result:
                    relations.append(wikidataID)

            logging.info(f'WikiData returned {len(nodes)} nodes')
            if len(nodes) > 0:
                placeholders = ', '.join("%s" for _ in nodes)
                query = f"UPDATE planet_osm_point SET cjk = %s WHERE wikidata IN ({placeholders})"
                cursor.execute(query, [place['font'], *nodes])
                rows_affected = cursor.rowcount
                logging.info(f"Updated {rows_affected} points")

            logging.info(f'WikiData returned {len(ways)} ways and {len(relations)} relations')
            ways += relations
            if len(ways) > 0:
                placeholders = ', '.join("%s" for _ in ways)
                query = f"UPDATE planet_osm_roads SET cjk = %s WHERE wikidata IN ({placeholders})"
                cursor.execute(query, [place['font'], *ways])
                rows_affected = cursor.rowcount
                logging.info(f"Updated {rows_affected} roads")
                query = f"UPDATE planet_osm_line SET cjk = %s WHERE wikidata IN ({placeholders})"
                cursor.execute(query, [place['font'], *ways])
                rows_affected = cursor.rowcount
                logging.info(f"Updated {rows_affected} other lines")
                query = f"UPDATE planet_osm_polygon SET cjk = %s WHERE wikidata IN ({placeholders})"
                cursor.execute(query, [place['font'], *ways])
                rows_affected = cursor.rowcount
                logging.info(f"Updated {rows_affected} polygons]")

            conn.commit()

if __name__ == '__main__':
    main()
