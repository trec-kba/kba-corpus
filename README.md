kba-corpus
==========

Tools for working with TREC KBA Corpora

For more info, run this:

   python kba_corpus.py  -h


The subcorpus_counter.py is an example Elastic Map Reduce (EMR) job
that uses yelp's mrjob to illustrate how to work with the KBA corpus.

subcorpus_counter.py reads in paths to individual chunk files in the
TREC KBA Stream Corpus 2012, loads them from s3, and counts things
about the data.

You can generate paths using this command -- note the particular
date-hour in this example is 2012-04-23-08:

  (for a in `s3cmd ls s3://aws-publicdatasets/trec/kba/kba-stream-corpus-2012/2012-04-23-08/ | grep xz.gpg | cut -c 32-`; 
  do echo http$a; done;) >& public_urls-2012-04-23-08.txt

You can get a list of all the date_hour strings here:

   s3cmd get s3://aws-publicdatasets/trec/kba/kba-stream-corpus-2012/dir-names.txt        
