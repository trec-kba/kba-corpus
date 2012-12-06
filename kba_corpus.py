#!/usr/bin/python
'''
Tools for processing the KBA Stream Corpus 2012

In addition to some basic utilities, the primary tool provided is
filter_annotated_docs, which the command line args to create a
filtered version of the corpus with only those docs that have
annotation.
'''

import os
import sys
try:
    import json
except:
    import simplejson as json
import time
import string
import hashlib
import traceback
import itertools
import subprocess
from cStringIO import StringIO

def log(mesg):
    sys.stderr.write('%s\n' % mesg)
    sys.stderr.flush()

try:
    ## import the thrift library
    from thrift import Thrift
    from thrift.transport import TTransport
    from thrift.protocol import TBinaryProtocol

    ## import the KBA-specific thrift types
    from kba_thrift.ttypes import StreamItem

except ImportError, exc:
    log(traceback.format_exc(exc))

def decrypt_and_uncompress(data, gpg_private=None, gpg_dir='gnupg-dir'):
    '''
    Given a data buffer of bytes, if gpg_key_path is provided, decrypt
    data using gnupg, and uncompress using xz.
    '''
    if gpg_private is not None:
        ### setup gpg for encryption
        if not os.path.exists(gpg_dir):
            os.makedirs(gpg_dir)
        gpg_child = subprocess.Popen(
            ['gpg', '--no-permission-warning', '--homedir', gpg_dir,
             '--import', gpg_private],
            stderr=subprocess.PIPE)
        s_out, errors = gpg_child.communicate()
        if errors:
            log('gpg logs to stderr, read carefully:\n\n%s' % errors)

        ## decrypt it, and free memory
        ## encrypt using the fingerprint for our trec-kba-rsa key pair
        gpg_child = subprocess.Popen(
            ## setup gpg to decrypt with trec-kba private key
            ## (i.e. make it the recipient), with zero compression,
            ## ascii armoring is off by default, and --output - must
            ## appear before --encrypt -
            ['gpg',   '--no-permission-warning', '--homedir', gpg_dir,
             '--trust-model', 'always', '--output', '-', '--decrypt', '-'],
            stdin =subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        ## communicate with child via its stdin 
        data, errors = gpg_child.communicate(data)
        if errors:
            log(errors)

    ## launch xz child
    xz_child = subprocess.Popen(
        ['xz', '--decompress'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    ## use communicate to pass the data incrementally to the child
    ## while reading the output, to avoid blocking 
    data, errors = xz_child.communicate(data)

    assert not errors, errors

    return data

def compress_and_encrypt(data, gpg_public=None, gpg_dir='gnupg-dir', gpg_recipient='trec-kba'):
    '''
    Given a data buffer of bytes compress it using xz, if gpg_public
    is provided, encrypt data using gnupg.
    '''
    ## launch xz child
    xz_child = subprocess.Popen(
        ['xz', '--compress'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE)
    ## use communicate to pass the data incrementally to the child
    ## while reading the output, to avoid blocking 
    data, errors = xz_child.communicate(data)

    assert not errors, errors

    if gpg_public is not None:
        ### setup gpg for encryption.  
        if not os.path.exists(gpg_dir):
            os.makedirs(gpg_dir)

        ## Load public key.  Could do this just once, but performance
        ## hit is minor and code simpler to do it everytime
        gpg_child = subprocess.Popen(
            ['gpg', '--no-permission-warning', '--homedir', gpg_dir,
             '--import', gpg_public],
            stderr=subprocess.PIPE)
        s_out, errors = gpg_child.communicate()
        if errors:
            log('gpg logs to stderr, read carefully:\n\n%s' % errors)

        ## encrypt using the fingerprint for our trec-kba-rsa key pair
        gpg_child = subprocess.Popen(
            ## setup gpg to decrypt with trec-kba private key
            ## (i.e. make it the recipient), with zero compression,
            ## ascii armoring is off by default, and --output - must
            ## appear before --encrypt -
            ['gpg',  '--no-permission-warning', '--homedir', gpg_dir,
             '-r', gpg_recipient, '-z', '0', '--trust-model', 'always',
             '--output', '-', '--encrypt', '-'],
            stdin =subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        ## communicate with child via its stdin 
        data, errors = gpg_child.communicate(data)
        if errors:
            log(errors)

    return data

def stream_items(thrift_data):
    '''
    Iterator over the StreamItems from a buffer of thrift data
    '''
    ## wrap it in a file obj, thrift transport, and thrift protocol
    transport = StringIO(thrift_data)        
    transport.seek(0)
    transport = TTransport.TBufferedTransport(transport)
    protocol = TBinaryProtocol.TBinaryProtocol(transport)

    ## read stream-item instances until input buffer is exhausted
    while 1:

        ## instantiate a StreamItem instance from kba_thrift
        doc = StreamItem()

        try:
            ## read it from the thrift protocol instance
            doc.read(protocol)
            ## This has deserialized the data analogous to
            ## json.loads(line).  The StreamItem from the thrift
            ## format is the analog of the JSON stream-item; see
            ## http://trec-kba.org/schemas/v1.0/stream-item.json

            ## yield is python primitive for iteration
            yield doc

        except EOFError:
            break

class TokenizationException(Exception):
    pass

class Token(object):
    ## use class properties as defaults
    line_number = None
    sentence_number = None
    is_sentence_boundary = False
    sentence_position = None
    token = r''
    lemma = r''
    pos = ''
    entity_type = ''
    start_byte = None
    end_byte = None
    urlname = None

    def __init__(self, line_number, sentence_number, fields):
        '''
        Takes a single line of Stanford NER data as it exists in the
        KBA 2012 corpus and instantiates the methods below.
        '''        
        self.line_number = line_number

        self.sentence_number = sentence_number

        self._fields = fields
        
        ## we should only ever see 1, 2, or 7 fields.  One means
        ## sentence boundary, seven is the normal case, and two
        ## happens when a URL is in the middle of a sentence.
        assert len(fields) in [1, 7], repr(fields)

        if len(fields) == 1:
            ## hit next sentence
            self.is_sentence_boundary = True
            return

        try:
            sentence_position, token, lemma, pos, entity_type, start_byte, end_byte = fields
            self.sentence_position = int(sentence_position) 
            self.token = token
            self.lemma = lemma
            self.pos = pos
            self.entity_type = entity_type
            self.start_byte = int(start_byte)
        except Exception, exc:
            raise TokenizationException('failed on Exception:\n%s\nfields:\n%r' % (traceback.format_exc(exc), fields))

        try:
            self.end_byte = int(end_byte)
        except ValueError:
            try:
                ## this has happened twice in the KBA 2012 corpus:
                end_byte, SENT_thing = end_byte.split('<')
                if end_byte == '':
                    ## we have seen getting no integer for the end_byte
                    self.end_byte = self.start_byte + len(self.token)
                else:
                    ## and also getting one...
                    self.end_byte = int(end_byte)
                ## we just ignore SENT_thing, which looks like this:
                ### 7       directly        directly        RB      O       2934    2942<SENT docid="doc.00000199" sentid="1">
                ### 1       Dil     Dil     NNP     O       820     <SENT docid="doc.00001612" sentid="1">
                    
            except Exception, exc:
                ## oops, is it something new?
                raise TokenizationException('failed on Exception:\n%s\nfields:\n%r' % (traceback.format_exc(exc), fields))

    def __str__(self):
        return '\t'.join([str(self.line_number), str(self.sentence_number), 
                          str(self.sentence_position)] + self._fields)

    def __repr__(self):
        return self.__str__()

    def get_dict(self):
        return {
            'is_sentence_boundary': self.is_sentence_boundary,
            'line_number': self.line_number,
            'sentence_number': self.sentence_number,
            ## note that sentence_position is one-based, not zero-based
            'sentence_position': self.sentence_position,
            'token': self.token,
            'lemma': self.lemma,
            'pos': self.pos,
            'entity_type': self.entity_type,
            'start_byte': self.start_byte,
            'end_byte': self.end_byte,
            'urlname': self.urlname
            }

    def get_tuple(self, minimal=False):
        '''
        returns (
            is_sentence_boundary,*
            line_number,
            sentence_number,
            sentence_position,
            token,*
            lemma,*
            pos,*
            entity_type,*
            start_byte,
            end_byte,
            urlname*
            )

        If minimal is True, then only the fields marked with * are included
        '''
        if minimal:
            return (
                self.is_sentence_boundary,
                self.token,
                self.lemma,
                self.pos,
                self.entity_type,
                self.urlname
                )
        else:
            return (
                self.is_sentence_boundary,
                self.line_number,
                self.sentence_number,
                ## note that sentence_position is one-based, not zero-based
                self.sentence_position,
                self.token,
                self.lemma,
                self.pos,
                self.entity_type,
                self.start_byte,
                self.end_byte,
                self.urlname
                )

def fielded_records(expected_field_counts, data):
    '''
    yields arrays of strings generated by splitting the data on tabs
    to get fields, and splitting on newlines to get records.

    Neither tabs nor newlines are passed through.

    Newlines appearing anywhere except the end of an expected number
    of fields are completely ignored.

    Empty line corresponds to a record with one field that is the
    empty string, because ''.split('\t') --> [''] rather than [].
    This means that zero should never appear in expected_field_counts.
    '''
    this_rec = []
    this_field = r''

    ## iterate over all bytes
    for this_byte in data:

        ## split fields on tabs, which are not included in the fields
        if this_byte == '\t':
            this_rec.append(this_field)
            this_field = r''

        ## split lines on newlines, unless we do not have enough fields
        elif this_byte == '\n':

            ## the number of fields accumulated thus far is one less
            ## than the number that will exist after we append
            ## this_field, even if this_field is empty '', which is
            ## what happens when the empty line is expected.
            if len(this_rec) + 1 in expected_field_counts:

                ## assume this is correct end of line
                # include this_field
                this_rec.append(this_field)

                ## yield the line
                yield this_rec

                ## reset the state machine
                this_rec = []
                this_field = r''

            else:
                ## have not yet accumulated enough fields in this
                ## record, so assume this newline is a bug: ignore it
                pass

        else:
            ## do not include \t or \n in fields
            this_field += this_byte

## global var for property names on StreamItem instances that could
## have 'ner' as one of their properties
content_item_types = ['body', 'title', 'anchor']

def tokens(doc, content='body'):
    '''
    Provides an iterator interface over the NER tokens

    The 'content' parameter can be any of 'body', 'title', 'anchor'
    '''
    assert content in content_item_types, \
        'content parameter was %s instead of %r' % (content, known_content)

    ## point to the requested content item
    content_item = getattr(doc, content)

    ## if requested ContentItem has empty ner, then end iteration
    if not content_item.ner:
        return

    ## use python's rendition of split('\n') which handles fence posts
    #lines = content_item.ner.splitlines()

    ## actually, do not use splitlines, because some tokens from
    ## Stanford NER have newlines in them.  This bug appears to only
    ## happen when the token is a URL.
    fields = list(fielded_records([1,7], content_item.ner))

    ## keep track of the sentence number in the loop below
    sentence_number = 0
    ## get the line numbers
    for line_number in range(len(fields)):
        ## construct a token
        try:
            tok = Token(line_number, sentence_number, fields[line_number])
        except TokenizationException, exc:
            log(traceback.format_exc(exc))
            log(content_item.ner)
            sys.exit('Failed on a TokenizationException in %s.' % doc.stream_id)
        
        ## increment sentence_number after we pass a boundary, note
        ## that boundary tokens are part of the *preceeding* sentence
        if tok.is_sentence_boundary:
            sentence_number += 1

        ## yield tokens until we finish all the lines and return
        yield tok

def sentences(doc, content='body'):
    '''
    Iterates over doc yielding arrays of Token instances.  Each array
    corresponds to a sentence.
    '''
    this_sentence = []
    for tok in tokens(doc, content=content):
        ## get all lines into a sentence, even if boundaries
        this_sentence.append(tok)

        if tok.is_sentence_boundary:
            ## output the sentence
            yield this_sentence

            ## reset
            this_sentence = []

    ## if last tok in doc was not boundary, then yield
    if this_sentence:
        yield this_sentence

def get_annotation(path_to_annotation):
    '''
    Reads a file of TREC KBA 2012 annotation and returns a dict keyed
    on stream_id.  This handles the format of the initial sample
    released publicly in mid June 2012, and also the training data
    released with the query topics to registered TREC participants.

    Final release of all 2012 annotation will be in the same format.
    '''
    ## load the data
    annotation_lines = open(path_to_annotation).read().splitlines()

    ## prepare a dict, keyed on stream_id
    annotation = {}
    
    for line in annotation_lines:
        ## ignore comments
        if line.startswith('#'):
            continue

        ## load the annotation data: first five fields are standard
        ## filter-run format for run submissions, and the sixth and
        ## seventh fields are the annotation.
        NIST_TREC, annotators, stream_id, urlname, score, \
                   relevance, contains_mention = line.split('\t')

        ## the judgments are integers:
        relevance = int(relevance)
        contains_mention = int(contains_mention)

        ## initialize the dict
        if stream_id not in annotation:
            annotation[stream_id] = {}

        ## docs might be annotated for multiple entities, so next
        ## level of 'annotation' data structure is another dict keyed
        ## on urlname:
        if urlname not in annotation[stream_id]:
            ## Multiple annotators may have seen this doc-entity pair,
            ## so need arrays for each of the two judgment types
            annotation[stream_id][urlname] = {'contains_mention': [],
                                              'relevance': []}

        ## append judgments to the two lists for this doc-entity pair
        annotation[stream_id][urlname]['contains_mention'].append(contains_mention)
        annotation[stream_id][urlname]['relevance'].append(relevance)

    return annotation


def filter_annotated_docs(annotation_path, thrift_dir, out_dir, date_hour,
                          gpg_private=None, gpg_public=None, gpg_dir='gnupg-dir'):
    '''
    reads in the compressed (and possibly encrypted) thrift of
    thrift_dir and generates a duplicate that is identical except for
    only docs with annotation are passed through.

    The resulting data is re-compressed.  If gpg_public is provided,
    then it is also re-encrypted.

    The new files are stored in out_dir/<date_hour>/ directories
    
    The stats.json files are ignored.
    '''
    annotation = get_annotation(annotation_path)

    ## prepare to write files an a temp version of out_dir.  We will
    ## do an atomic rename of this dir after it is finished.
    out_dir = os.path.join(out_dir, date_hour)
    tmp_out_dir = out_dir + '.partial'

    if not os.path.exists(tmp_out_dir):
        os.makedirs(tmp_out_dir)

    ## loop over all files from input dir
    num_files = 0
    for i_fname in os.listdir(os.path.join(thrift_dir, date_hour)):
        ## ignore other files, e.g. stats.json
        if not (i_fname.endswith('.xz.gpg') or i_fname.endswith('.xz')):
            continue

        ## get subcorpus name and original_md5 for use in new output
        ## file names
        subcorpus, o_content_md5, _xz, _gpg = i_fname.split('.')
        assert subcorpus in ['news', 'linking', 'social'], subcorpus

        ## construct input file path
        i_fpath = os.path.join(thrift_dir, date_hour, i_fname)

        ## load the encrypted data
        i_encrypted_data = open(i_fpath).read()

        assert len(i_encrypted_data) > 0, 'failed to load: %s' % fpath

        ## decrypt and uncompress using subprocess tools above
        i_thrift_data = decrypt_and_uncompress(i_encrypted_data, gpg_private, gpg_dir)

        ## compare md5 hashes:
        i_content_md5 = hashlib.md5(i_thrift_data).hexdigest()
        assert i_content_md5 == i_fname.split('.')[1], \
            '%r != %r' % (i_content_md5, o_content_md5)

        ## Make output file obj for thrift, wrap in protocol
        o_transport = StringIO()
        o_protocol = TBinaryProtocol.TBinaryProtocol(o_transport)

        ## iterate over input stream items
        num_annotated = 0
        for stream_item in stream_items(i_thrift_data):
            
            ## only keep those docs that have annotation
            if not stream_item.stream_id in annotation:
                continue
            else:
                log('%s has annotation for %s' % (
                    stream_item.stream_id,
                    ', '.join(annotation[stream_item.stream_id].keys())))

            ## Every stream_item has a source_metadata JSON string,
            ## which we can load and extend to include the annotation:
            source_metadata = json.loads(stream_item.source_metadata)
            source_metadata['annotation'] = annotation[stream_item.stream_id]

            ## We can just replace the source_metadata string, and
            ## thrift will serialize it into output o_protocol
            stream_item.source_metadata = json.dumps(source_metadata)

            ## write modified stream_item object to new output file
            stream_item.write(o_protocol)

            num_annotated += 1

        if num_annotated == 0:
            ## do not save an empty file
            continue
        
        ## prepare to write out the new file
        o_transport.seek(0)
        o_thrift_data = o_transport.getvalue()

        ## compute md5 of uncompressed data
        o_content_md5 = hashlib.md5(o_thrift_data).hexdigest()
        
        ## construct output filename
        o_fname = '%s.%s.%s.xz' % (subcorpus, o_content_md5, i_content_md5)

        ## put gpg extension only if we are encrypting output
        if gpg_public is not None:
            o_fname += '.gpg'

        # output file
        o_fpath = os.path.join(tmp_out_dir, o_fname)
        
        ## temporary output file called .partial, which will be
        ## atomically renamed upon completion.  This provides
        ## robustness against crashes or restarts in condor.
        tmp_out_fpath = o_fpath + '.partial'

        ## compress and encrypt the data
        o_encrypted_data = compress_and_encrypt(o_thrift_data, gpg_public, gpg_dir)

        ## write it to the tmp file 
        fh = open(tmp_out_fpath, 'wb')
        fh.write(o_encrypted_data)
        fh.close()

        ## atomic move of fully written file
        os.rename(tmp_out_fpath, o_fpath)

        ## loop to next input thrift file
        num_files += 1

        ## free memory
        o_encrypted_data = None
        o_thrift_data = None

    ## atomic move of tmp_out_dir to out_dir
    log('renaming %s --> %s' % (tmp_out_dir, out_dir))
    os.rename(tmp_out_dir, out_dir)
    log('Done!  created %d files' % num_files)

if __name__ == '__main__':
    ## argparse is in python 2.7, and is can be used on early python
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('annotation', help='path to file of annotation data to use in filtering')
    parser.add_argument('thrift_dir', help='path to directory of date_hour dirs containing compressed thrift files, possibly encrypted')
    parser.add_argument('out_dir', help='path to create directory for holding date_hour dirs new thrift files, also compressed and possibly encrypted.')
    parser.add_argument('date_hour', help='name of date_hour to process')
    parser.add_argument('--private', default=None, help='Provide GPG decryption (private) key for reading corpus')
    parser.add_argument('--public', default=None, help='Provide GPG encryption (public) key for re-saving corpus')
    parser.add_argument('--gpgdir', default='gnupg-dir', help='dir for storing gpg files, e.g. keys')
    parser.add_argument('--path', nargs='?', action='append', help='add path to python library dirs, can be used multiple times.')
    args = parser.parse_args()

    ## add any needed paths to python path, so we can import things
    ## that are not in standard python
    map(sys.path.append, args.path)
    
    ## import the thrift library
    from thrift import Thrift
    from thrift.transport import TTransport
    from thrift.protocol import TBinaryProtocol

    ## import the KBA-specific thrift types
    from kba_thrift.ttypes import StreamItem

    filter_annotated_docs(args.annotation, args.thrift_dir, args.out_dir, args.date_hour, gpg_private=args.private, gpg_public=args.public, gpg_dir=args.gpgdir)
