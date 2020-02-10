/**
    Consider linting before running
    see:  https://jenkins.io/doc/book/pipeline/development/
    curl -X POST -H $(curl "127.0.0.1/crumbIssuer/api/xml?xpath=concat(//crumbRequestField,\":\",//crumb)") -F "jenkinsfile=<Jenkinsfile" 127.0.0.1/pipeline-model-converter/validate


**/

pipeline {

    agent any

    /*triggers {
         Run every Monday at 5pm
         cron('H 17 * * 1')

    }*/

    environment {
        // Pin dates and day to beginning of run.
        START_DATE = sh(
            script: 'date +%Y-%m-%d',
            returnStdout: true
        ).trim()

        START_DAY = sh(
            script: 'date +%A',
            returnStdout: true
        ).trim()

        DATA_RELEASE_VERSION = sh(
            script: 'date +%Y%m',
            returnStdout: true
        ).trim()


        DIPPERCACHE = 'https://archive.monarchinitiative.org/DipperCache'

        MONARCH_DATA_FS = 'monarch-ttl-prod'
        DIPPER = "venv/bin/python dipper-etl.py --skip_tests --data_release_version $DATA_RELEASE_VERSION"

        // https://issues.jenkins-ci.org/browse/JENKINS-47881
        DATA_DEST = "${env.RELEASE ? '/var/www/data/dev/' : '/var/www/data/experimental/'}"

        /* human, mouse, zebrafish, fly, worm */
        COMMON_TAXON = "9606,10090,7955,7227,6239"
        /* 10116 is rat and might be included if found relevent where it is now missing */

    }

    options {
        buildDiscarder(logRotator(numToKeepStr: '14'))
    }

    stages {
        stage('Build dipper package') {
            steps {
                dir('./config') {
                    git(
                        url: 'https://github.com/monarch-initiative/configs.git',
                        credentialsId: '3ca28d15-5fa8-46b1-a2ac-a5a483694f5b',
                        branch: 'master'
                    )
                    sh '''
                        cd .. && cp config/Dipper/conf.yaml ./dipper/conf.yaml
                        virtualenv -p /usr/bin/python3.6 venv
                        venv/bin/pip install -r requirements.txt
                        venv/bin/pip install -r requirements/all-sources.txt

                        echo "Clean up previous runs"
                        rm -f ./out/*.ttl ./out/*.nt
                        echo "Anything remaining should not still be in './out'"
                        ls -l ./out
                        rm -fr ./out
                    '''
                }
            }
        }
        stage('Generate monarch owl and rdf') {
            parallel {
                stage("Process sources that call OMIM") {
                    stages {
                        stage("ETL OMIM") {
                            when {
                                anyOf {
                                    expression { env.RUN_ALL != null }
                                    expression { env.OMIM != null }
                                }
                            }
                            steps {
                                sh '''
                                    SOURCE=omim
                                    $DIPPER --sources $SOURCE -q
                                    scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                                '''
                            }
                        }
                        stage("ETL NCBI Gene") {
                            when {
                                anyOf {
                                    expression { env.RUN_ALL != null }
                                    expression { env.NCBIGENE != null }
                                }
                            }
                            steps {
                                sh '''
                                    SOURCE=ncbigene
                                    $DIPPER --sources $SOURCE \
                                        --taxon $COMMON_TAXON,10116,28377,3702,9913,9615,9031,44689,9796,9544,13616,9258,9598,9823,4896,31033,8364,9685,559292
                                    scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                                '''
                            }
                        }
                        stage("ETL OMIA") {
                            when {
                                anyOf {
                                    expression { env.RUN_ALL != null }
                                    expression { env.OMIA != null }
                                }
                            }
                            steps {
                                sh '''
                                    SOURCE=omia
                                    $DIPPER --sources $SOURCE
                                    scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                                '''
                            }
                        }
                        stage("ETL HGNC") {
                            when {
                                anyOf {
                                    expression { env.RUN_ALL != null }
                                    expression { env.HGNC != null }
                                }
                            }
                            steps {
                                sh '''
                                    SOURCE=hgnc
                                    $DIPPER --sources $SOURCE
                                    scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                                '''
                            }
                        }
                        stage("ETL KEGG") {
                            when {
                                anyOf {
                                    expression { env.RUN_ALL != null }
                                    expression { env.KEGG != null }
                                }
                            }
                            steps {
                                sh '''
                                    SOURCE=kegg
                                    $DIPPER --sources $SOURCE
                                    scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                                '''
                            }
                        }
                        stage("ETL Gene Reviews") {
                            when {
                                anyOf {
                                    expression { env.RUN_ALL != null }
                                    expression { env.GENE_REVIEWS != null }
                                }
                            }
                            steps {
                                dir('./data-boutique') {
                                    git(
                                        url: 'https://github.com/monarch-initiative/data-boutique.git',
                                        credentialsId: '3ca28d15-5fa8-46b1-a2ac-a5a483694f5b',
                                        branch: 'master'
                                    )
                                    sh '''
                                        SOURCE=genereviews
                                        cd .. && mkdir -p raw/genereviews/books
                                        cp ./data-boutique/GeneReviewsBooks/* ./raw/genereviews/books/
                                        $DIPPER --sources $SOURCE
                                    scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                                    '''
                                }
                            }
                        }
                    }
                }
                stage("Generate monarch merged owl file") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.MONARCH_OWL != null }
                        }
                    }
                    steps {
                        dir('./create-monarch-owl') {deleteDir()}
                        dir('./create-monarch-owl') {
                            sh """
                                wget --quiet --timestamping http://release.geneontology.org/2019-10-07/bin/owltools

                                chmod +x owltools

                                java -Xmx100g -jar owltools http://purl.obolibrary.org/obo/upheno/monarch.owl --merge-import-closure --remove-disjoints --remove-equivalent-to-nothing-axioms -o monarch-merged.owl

                                # Hack to resolve https://github.com/monarch-initiative/monarch-ontology/issues/16
                                # Hack to normalize omim and hgnc IRIs

                                sed -i "/owl#ReflexiveProperty/d;\
                                    s~http://purl.obolibrary.org/obo/OMIMPS_~http://www.omim.org/phenotypicSeries/PS~;\
                                    s~http://purl.obolibrary.org/obo/OMIM_~http://omim.org/entry/~;\
                                    s~http://identifiers.org/omim/~http://omim.org/entry/~;\
                                    s~http://identifiers.org/hgnc/~https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/HGNC:~;\
                                    s~http://www.genenames.org/cgi-bin/gene_symbol_report?hgnc_id=~https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/HGNC:~;\
                                    s~http://www.informatics.jax.org/marker/MGI:~http://www.informatics.jax.org/accession/MGI:~;\
                                    s~http://www.ncbi.nlm.nih.gov/gene/~https://www.ncbi.nlm.nih.gov/gene~" \
                                    ./monarch-merged.owl

                                scp monarch-merged.owl monarch@$MONARCH_DATA_FS:/var/www/data/owl/
                            """
                        }
                    }
                }
                stage("ETL StringDb") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.STRING_DB != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=stringdb
                            $DIPPER --sources $SOURCE --taxon $COMMON_TAXON,10116 --version 11.0
                            scp ./out/string.ttl ./out/string_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
                stage("ETL Panther") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.PANTHER != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=panther
                            mkdir -p raw/panther
                            $DIPPER --sources $SOURCE --taxon $COMMON_TAXON,10116,9913,9031,9796,9823,8364,9615 --dest_fmt nt
                            scp ./out/${SOURCE}.nt ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
                stage("ETL AnimalQTLdb") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.ANIMALQTLDB != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=animalqtldb
                            $DIPPER --sources $SOURCE
                            scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
                stage("ETL Bgee") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.BGEE != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=bgee
                            $DIPPER --sources $SOURCE --limit 20 --taxon $COMMON_TAXON,10116 # --version bgee_v13_2

                            echo "check statement count and if well-formed?"
                            rapper -i turtle -c ./out/bgee.ttl
                            scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
                stage("ETL FlyBase") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.FLYBASE != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=flybase
                            $DIPPER --sources $SOURCE
                            scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
                stage("ETL Biogrid") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.BIOGRID != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=biogrid
                            $DIPPER --sources $SOURCE --taxon $COMMON_TAXON
                            scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
                stage("ETL ClinVar") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.CLINVAR != null }
                        }
                    }
                    steps {
                        sh '''
                            mkdir -p out
                            mkdir -p raw/clinvar && cd raw/clinvar
                            # these are available via http in DipperCache too
                            # ftp://ftp.ncbi.nlm.nih.gov/pub/clinvar/xml/ClinVarFullRelease_00-latest.xml.gz
                            wget --quiet --timestamping "$DIPPERCACHE/clinvar/ClinVarFullRelease_00-latest.xml.gz"
                            wget --quiet --timestamping "$DIPPERCACHE/clinvar/gene_condition_source_id"
                            cd -

                            export PYTHONPATH=.:$PYTHONPATH
                            venv/bin/python ./dipper/sources/ClinVar.py
                            scp ./out/clinvar.nt monarch@$MONARCH_DATA_FS:${DATA_DEST}/clinvar.nt
                        '''
                    }
                }
                stage("ETL Coriell") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.CORIELL != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=coriell
                            $DIPPER --sources $SOURCE
                            scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
                stage("ETL CTD") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.CTD != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=ctd
                            $DIPPER --sources $SOURCE
                            scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
                stage("ETL Ensembl") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.ENSEMBL != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=ensembl
                            $DIPPER --sources $SOURCE --taxon $COMMON_TAXON
                            scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
                stage("ETL Elements of Morphology") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.EOM != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=eom
                            $DIPPER --sources $SOURCE
                            scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
                stage("ETL Gene Ontology Associations") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.GO != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=go
                            $DIPPER --sources $SOURCE --taxon \
                                $COMMON_TAXON,10116,4896,5052,559292,5782,9031,9615,9823,9913
                            scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
                stage("ETL GWAS Catalog") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.GWASCATALOG != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=gwascatalog
                            $DIPPER --sources $SOURCE
                            scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
                stage("ETL HPO Annotations") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.HPOA != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=hpoa
                            $DIPPER --sources $SOURCE
                            scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
                stage("ETL IMPC") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.IMPC != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=impc
                            $DIPPER --sources $SOURCE
                            scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
                stage("ETL MGISlim") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.MGISLIM != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=mgislim
                            $DIPPER --sources $SOURCE
                            scp ./out/mgislim.ttl ./out/mgislim_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
                stage("ETL MGI") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.MGI != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=mgi
                            $DIPPER --sources $SOURCE
                            scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
                stage("ETL MMRRC") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.MMRRC != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=mmrrc
                            $DIPPER --sources $SOURCE
                            scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
                stage("ETL Monarch Boutique") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.MONARCH != null }
                        }
                    }
                    steps {
                        dir('./data-boutique-b') {
                            git(
                                url: 'https://github.com/monarch-initiative/data-boutique.git',
                                credentialsId: '3ca28d15-5fa8-46b1-a2ac-a5a483694f5b',
                                branch: 'master'
                            )
                            sh '''
                                SOURCE=monarch
                                cd .. && mkdir -p raw/monarch
                                cp -r data-boutique-b/OMIA-disease-phenotype ./raw/monarch/
                                $DIPPER --sources $SOURCE
                                scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                            '''
                        }
                    }
                }
                stage("ETL monochrom") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.MONOCHROM != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=monochrom
                            $DIPPER --sources $SOURCE
                            scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
                stage("ETL MPD") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.MPD != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=mpd
                            $DIPPER --sources $SOURCE
                            scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
                stage("ETL Orphanet") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.ORPHANET != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=orphanet
                            $DIPPER --sources $SOURCE
                            scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
                stage("ETL Reactome") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.REACTOME != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=reactome
                            $DIPPER --sources $SOURCE
                            scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
                stage("ETL Wormbase") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.WORMBASE != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=wormbase
                            $DIPPER --sources $SOURCE --dest_fmt nt
                            scp ./out/${SOURCE}.nt ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
                stage("ETL ZFINSlim") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.ZFINSLIM != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=zfinslim
                            $DIPPER --sources $SOURCE
                            scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
                stage("ETL ZFIN") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.ZFIN != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=zfin
                            $DIPPER --sources $SOURCE
                            scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
                stage("ETL RGD") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.RGD != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=rgd
                            $DIPPER --sources $SOURCE
                            scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
                stage("ETL SGD") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.SGD != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=sgd
                            $DIPPER --sources $SOURCE --data_release_version $DATA_RELEASE_VERSION
                            scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
                stage("ETL MyChem Info") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.MYCHEM != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=mychem
                            $DIPPER --sources $SOURCE
                            scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
                stage("ETL UCSCBands") {
                    when {
                        anyOf {
                            expression { env.RUN_ALL != null }
                            expression { env.UCSCBANDS != null }
                        }
                    }
                    steps {
                        sh '''
                            SOURCE=ucscbands
                            $DIPPER --sources $SOURCE
                            scp ./out/${SOURCE}.ttl ./out/${SOURCE}_dataset.ttl monarch@$MONARCH_DATA_FS:$DATA_DEST
                        '''
                    }
                }
            }
        }
    }
}
