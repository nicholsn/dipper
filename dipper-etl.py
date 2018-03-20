#!/usr/bin/env python3

import argparse
import logging
import unittest
import importlib
import time

# TODO PYLINT not finding imports
# Unable to import 'tests.test_general'
# No name 'utils' in module 'dipper'
# Invalid constant name "test_suite"
from tests.test_general import GeneralGraphTestCase
from dipper.utils.TestUtils import TestUtils
from dipper.utils.GraphUtils import GraphUtils


requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.ERROR)


test_suite = unittest.TestLoader().loadTestsFromTestCase(GeneralGraphTestCase)


def main():
    # TODO this should be generated by looking in the dipper/sources directory
    # or read from a sources/dataset/config yaml or dir of yamls
    source_to_class_map = {
        # 'facebase_alpha': 'FaceBase_alpha',
        'hpoa': 'HPOAnnotations',   # ~3 min
        'zfin': 'ZFIN',
        'omim': 'OMIM',  # full file takes ~15 min, due to required throttling
        'biogrid': 'BioGrid',  # interactions file takes <10 minutes
        'mgi': 'MGI',
        'impc': 'IMPC',
        # Panther takes ~1hr to map 7 species-worth of associations
        'panther': 'Panther',
        'oma': 'OMA',
        'ncbigene': 'NCBIGene',  # takes about 4 minutes to process 2 species
        'ucscbands': 'UCSCBands',
        'ctd': 'CTD',
        'genereviews': 'GeneReviews',
        'eom': 'EOM',  # Takes about 5 seconds.
        'coriell': 'Coriell',
        # 'clinvar': 'ClinVar',                   # takes ~ half hour
        # 'clinvarxml_alpha': 'ClinVarXML_alpha', # takes ~ five minutes
        'monochrom': 'Monochrom',
        'kegg': 'KEGG',
        'animalqtldb': 'AnimalQTLdb',
        'ensembl': 'Ensembl',
        'hgnc': 'HGNC',
        'orphanet': 'Orphanet',
        'omia': 'OMIA',
        'flybase': 'FlyBase',
        'mmrrc': 'MMRRC',
        'wormbase': 'WormBase',
        'mpd': 'MPD',
        'gwascatalog': 'GWASCatalog',
        'monarch': 'Monarch',
        'go': 'GeneOntology',
        'reactome': 'Reactome',
        'udp': 'UDP',
        'mgi-slim': 'MGISlim',
        'zfin-slim': 'ZFINSlim',
        'bgee': 'Bgee',
        'mydrug': 'MyDrug',
        'stringdb': 'StringDB',
        'rgd': 'RGD',
        'sgd': 'SGD',
	'mychem': 'MyChem'
    }

    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(
        description='Dipper: Data Ingestion Pipeline for SciGraph',
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument(
        '-g', '--graph', type=str, default="rdf_graph",
        help='graph type: rdf_graph, streamed_graph')
    parser.add_argument(
        '-s', '--sources', type=str, required=True,
        help='comma separated list of sources')
    parser.add_argument(
        '-l', '--limit', type=int,
        help='limit number of rows')
    parser.add_argument(
        '--parse_only', action='store_true',
        help='parse files without writing')
    parser.add_argument(
        '--fetch_only', action='store_true',
        help='fetch sources without parsing')
    parser.add_argument('-f', '--force', action='store_true',
                        help='force re-download of files')
    parser.add_argument(
        '--no_verify',
        help='ignore the verification step', action='store_true')
    parser.add_argument('--query', help='enter in a sparql query', type=str)
    parser.add_argument(
        '-q', '--quiet',
        help='turn off info logging', action="store_true")
    parser.add_argument(
        '--debug', help='turn on debug logging', action="store_true")
    parser.add_argument(
        '--skip_tests', help='skip any testing', action="store_true")

    # Blank Nodes can't be visualized in Protege, default to Skolemizing them
    parser.add_argument(
        '-b', '--use_bnodes',
        help="use blank nodes instead of skolemizing", action="store_true",
        default=False)

    # TODO this should live in a global data file
    #   and the same filter be applied to all sources
    parser.add_argument(
        '-t', '--taxon', type=str,
        help='Add a taxon constraint on a source. Enter 1+ NCBITaxon numbers,'
        ' comma delimited\n'
        'Implemented taxa per source\n'
        'NCBIGene: 9606,10090,7955\n'
        'Panther: 9606,10090,10116,7227,7955,6239,8355\n'
        'BioGrid: 9606,10090,10116,7227,7955,6239,8355\n'
        'UCSCBands: 9606\n'
        'GO: 9606,10090,10116,7227,7955,6239,9615,9823,9031,9913')
    parser.add_argument(
        '-o', '--test_only',
        help='only process and output the pre-configured test subset',
        action="store_true")

    parser.add_argument(
        '--dest_fmt',
        help='serialization format: [turtle], nt, nquads, rdfxml, n3, raw',
        type=str)

    parser.add_argument(
        '--version', '-v',
        help='version of source',
        type=str)

    args = parser.parse_args()
    tax_ids = None
    if args.taxon is not None:
        tax_ids = [int(t) for t in args.taxon.split(',')]

    taxa_supported = [  # these are not taxa
        'Panther', 'NCBIGene', 'BioGrid', 'UCSCBands', 'GeneOntology',
        'Bgee', 'Ensembl', 'StringDB', 'OMA']

    formats_supported = [
        'turtle', 'ttl',
        'ntriples', 'nt',
        'nquads', 'nq',
        'rdfxml', 'xml',
        'notation3', 'n3',
        'raw']

    if args.quiet:
        logging.basicConfig(level=logging.ERROR)
    else:
        if args.debug:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

    if not args.use_bnodes:
        logger.info("Will Skolemize Blank Nodes")

    if args.query is not None:
        test_query = TestUtils()
        for source in args.sources.split(','):
            source = source.lower()
            mysource = source_to_class_map[source]()

            # import source lib
            module = "dipper.sources.{0}".format(mysource)
            imported_module = importlib.import_module(module)
            source_class = getattr(imported_module, mysource)

            test_query.check_query_syntax(args.query, source_class)
            test_query.load_graph_from_turtle(source_class)

        print(test_query.query_graph(args.query, True))
        exit(0)

    # run initial tests
    if (args.no_verify or args.skip_tests) is not True:
        unittest.TextTestRunner(verbosity=2).run(test_suite)

    # set serializer
    if args.dest_fmt is not None:
        if args.dest_fmt in formats_supported:
            if args.dest_fmt == 'ttl':
                args.dest_fmt = 'turtle'
            elif args.dest_fmt == 'ntriples':
                args.dest_fmt = 'nt'
            elif args.dest_fmt == 'nq':
                args.dest_fmt = 'nquads'
            elif args.dest_fmt == 'xml':
                args.dest_fmt = 'rdfxml'
            elif args.dest_fmt == 'notation3':
                args.dest_fmt = 'n3'
        else:
            logger.error(
                "You have specified an invalid serializer: %s", args.dest_fmt)

            exit(0)
    else:
        args.dest_fmt = 'turtle'

    # iterate through all the sources
    for source in args.sources.split(','):
        logger.info("\n******* %s *******", source)
        source = source.lower()
        src = source_to_class_map[source]

        # import source lib
        module = "dipper.sources.{0}".format(src)
        imported_module = importlib.import_module(module)
        source_class = getattr(imported_module, src)
        mysource = None
        # arg factory
        source_args = dict(
            graph_type=args.graph
        )
        source_args['are_bnodes_skolemized'] = not args.use_bnodes
        if src in taxa_supported:
            source_args['tax_ids'] = tax_ids
        if args.version:
            source_args['version'] = args.version

        mysource = source_class(**source_args)
        if args.parse_only is False:
            start_fetch = time.clock()
            mysource.fetch(args.force)
            end_fetch = time.clock()
            logger.info("Fetching time: %d sec", end_fetch-start_fetch)

        mysource.settestonly(args.test_only)

        # run tests first
        if (args.no_verify or args.skip_tests) is not True:
            suite = mysource.getTestSuite()
            if suite is None:
                logger.warning(
                    "No tests configured for this source: %s", source)
            else:
                unittest.TextTestRunner(verbosity=2).run(suite)
        else:
            logger.info("Skipping Tests for source: %s", source)

        if args.test_only is False and args.fetch_only is False:
            start_parse = time.clock()
            mysource.parse(args.limit)
            end_parse = time.clock()
            logger.info("Parsing time: %d sec", end_parse-start_parse)
            if args.graph == 'rdf_graph':
                logger.info("Found %d nodes", len(mysource.graph))

                # Add property axioms
                start_axiom_exp = time.clock()
                logger.info("Adding property axioms")

                properties = GraphUtils.get_properties_from_graph(mysource.graph)
                GraphUtils.add_property_axioms(mysource.graph, properties)
                end_axiom_exp = time.clock()
                logger.info("Property axioms added: %d sec",
                            end_axiom_exp-start_axiom_exp)

                start_write = time.clock()
                mysource.write(fmt=args.dest_fmt)
                end_write = time.clock()
                logger.info("Writing time: %d sec", end_write-start_write)
        # if args.no_verify is not True:

        #    status = mysource.verify()
        #    if status is not True:
        #        logger.error(
        #            'Source %s did not pass verification tests.', source)
        #        exit(1)
        # else:
        #    logger.info('skipping verification step')
        logger.info('***** Finished with %s *****', source)
    # load configuration parameters
    # for example, keys

    logger.info("All done.")


if __name__ == "__main__":
    main()

###########################
