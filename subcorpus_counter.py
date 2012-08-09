'''
reads in paths to individual chunk files in the TREC KBA Stream Corpus
2012, loads them from s3, and counts things about the data

Uses mrjob to run itself in hadoop on AWS EMR

You can generate paths using this command:

  (for a in `s3cmd ls s3://aws-publicdatasets/trec/kba/kba-stream-corpus-2012/2012-04-23-08/ | grep xz.gpg | cut -c 32-`; do echo http$a; done;) >& public_urls-2012-04-23-08.txt
                                                                             ^^^^^^^^^^^^^
                                                                               date_hour

You can get a list of all the date_hour strings here:

   s3cmd get s3://aws-publicdatasets/trec/kba/kba-stream-corpus-2012/dir-names.txt        

'''

import re
import os
import sys
import time
import urllib
import syslog
import traceback

## you can configure boto within EMR by modifying your copy of the
## shell scripts in s3://trec-kba-emr/emr-setup to create ~/.boto file
#import boto

## load mrjob components
import mrjob.emr
from mrjob.job import MRJob
import mrjob.protocol

import kba_corpus

class SubcorpusCounter(MRJob):
    INPUT_PROTOCOL  = mrjob.protocol.RawValueProtocol

    def mapper(self, empty, public_url):
        '''
        Takes as input a public URL to a TREC KBA 2012 chunk file,
        which it then loads, decrypts, uncompresses, and deserializes,
        so that it can count the number of NER tokens.

        This emits keys equal to the subcorpus name ('news',
        'linking', or 'social') and value is a two tuple of integers.
        First integer in the two-tuple is equal to the number of NER
        tokens, and second the number of sentences as tokenized by
        Stanford NER.
        '''
        
        subcorpus_name = None
        num_ner_tokens = 0
        num_ner_sentences = 0

        try:
            ## fetch the file to a local tempfile
            kba_corpus.log('fetching %r' % public_url)
            data = urllib.urlopen(public_url.strip()).read()

            ## shell out to gpg and xz to get the thrift
            thrift_data = kba_corpus.decrypt_and_uncompress(
                data, 'kba_corpus.tar.gz/trec-kba-rsa.secret-key')

            ## iterate over all the docs in this chunk            
            for stream_item in kba_corpus.stream_items(thrift_data):
                ## this should be the same every time, could assert
                subcorpus_name = stream_item.source

                ## for fun, keep counters on how many docs have NER or not
                if not (stream_item.body.ner or stream_item.anchor.ner or stream_item.title.ner):
                    self.increment_counter('SubcorpusCounter', 'no-NER', 1)
                else:
                    self.increment_counter('SubcorpusCounter', 'hasNER', 1)

                ## tell hadoop we are still alive
                self.increment_counter('SubcorpusCounter', 'StreamItemsProcessed', 1)

                ## iterate over sentences to generate the two counts
                for content in ['body', 'anchor', 'title']:
                    for sentence in kba_corpus.sentences(stream_item, content=content):
                        num_ner_tokens += len(sentence)
                        num_ner_sentences += 1

        except Exception, exc:
            ## oops, log verbosely, including with counters (maybe too clever)
            kba_corpus.log(traceback.format_exc(exc))
            key = 'FAILED-%s' % re.sub('\s+', '-', str(exc))
            ## could emit this, but that would polute the output
            # yield key, public_url
            self.increment_counter('Errors', key, 1)

        else:
            ## it must have all worked, so emit data
            yield subcorpus_name, (num_ner_tokens, num_ner_sentences)

        finally:
            ## help hadoop keep track
            self.increment_counter('SkippingTaskCounters','MapProcessedRecords',1)

    ## This reducer works intermittently, perhaps a memory problem and
    ## just need a newer version of mrjob?  This is not required for
    ## illustrating how to begin interacting with the corpus, so
    ## commenting out.
    #def reducer(self, source, counts):
    #    '''
    #    Sums up all the counts for a given source
    #    '''
    #    num_ner_tokens = 0
    #    num_ner_sentences = 0
    #    for this_num_ner_tokens, this_num_ner_sentences in counts:
    #        num_ner_tokens    += this_num_ner_tokens
    #        num_ner_sentences += this_num_ner_sentences
    #    yield source, (num_ner_tokens, num_ner_sentences)
    #    self.increment_counter('SkippingTaskCounters','ReduceProcessedRecords',1)

if __name__ == '__main__':
    SubcorpusCounter.run()
