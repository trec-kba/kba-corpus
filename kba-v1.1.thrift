
/**
 * These thrift definitions provide general structures for storing
 * text corpora that have been transformed for ease of processing and
 * may have annotation.
 *
 * This v1.1 improves on the original kba.thrift file used for the
 * TREC Knowledge Base Acceleration evaluation in NIST's TREC 2012
 * conference.
 *
 * This is released as open source software under the MIT X11 license:
 * Copyright (c) 2012 Computable Insights.
 *
 * Permission is hereby granted, free of charge, to any person
 * obtaining a copy of this software and associated documentation
 * files (the "Software"), to deal in the Software without
 * restriction, including without limitation the rights to use, copy,
 * modify, merge, publish, distribute, sublicense, and/or sell copies
 * of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be
 * included in all copies or substantial portions of the Software.
 * 
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
 * EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
 * MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
 * BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
 * ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
 * CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */
namespace java kba
namespace py kba

/**
 * StreamTime is a timestamp measured in seconds since the 1970 epoch.
 * epoch_ticks is always in the UTC timezone.  This is used in several
 * structs below to record various moments in history.
 */
struct StreamTime {
  1: double epoch_ticks,
  2: string zulu_timestamp,
}

/**
 * ContentItem contains raw data, an indication of its character
 * encoding, and various transformed versions of the raw data.
 *
 * 'cleansed' is generated from 'raw', and 'ner' is generated from
 * 'cleansed.'  Generally, 'cleansed' is a tag-stripped version of
 * 'raw', and 'ner' is the output of a named entity recognizer that
 * generates one-word-per-line output.
 *
 * For the kba-stream-corpus-2012, the specific tag-stripping and NER
 * configurations were:
 *   'raw' --> boilerpipe 1.2.0 KeepEverything --> 'cleansed'
 *
 *   'cleansed' -> Stanford CoreNLP ver 1.2.0 with annotators
 *        {tokenize, cleanxml, ssplit, pos, lemma, ner}, property
 *        pos.maxlen=100" --> 'ner'
 */
struct ContentItem {
  // original download, raw byte array
  1: binary raw, 
  
  // guessed from raw and/or headers, e.g. python requests library
  2: string encoding, 

  // all visible text, e.g. from boilerpipe 1.2.0 KeepEverything
  3: optional binary cleansed, 

  // One-Word-Per-Line (OWLP) tokenization and sentence chunking with
  // part-of-speech, lemmatization, and NER classification.
  4: optional binary ner, 

  // a correctly parsed and reformatted HTML version of raw with each
  // HTML tag on its own line separate from lines with visible text,
  // made with, e.g., BeautifulSoup(raw).prettify()
  5: optional binary html 
}

/**
 * SourceMetadata is a serialized JSON object (not an array, rather a
 * dict).  The SourceMetadata might not have a schema.  It can be any
 * general JSON object.
 *
 * For the kba-stream-corpus-2012, the SourceMetadata was always one
 * of these schemas where 'news', 'social', 'linking' is the string
 * found in CorpusItem.source
 *  - http://trec-kba.org/schemas/v1.0/news-metadata.json
 *  - http://trec-kba.org/schemas/v1.0/linking-metadata.json
 *  - http://trec-kba.org/schemas/v1.0/social-metadata.json
 *
 */
typedef binary SourceMetadata

/**
 * Offset and OffsetType are used by Annotation to identify the
 * portion of a ContentItem that a human labeled with a tag.
 */
enum OffsetType {
  // annotation applies to a range of line numbers in a
  // one-word-per-line output
  OWPL,

  // annotation applies to a range of bytes
  BYTEOFFSET,

  // annotation applies to a range of chars
  CHAROFFSET,
}

/*
 * Offset specifies a range within a field of data in a ContentItem
 */
struct Offset {
  // if true, then annotation applies to entire StreamItem, so no
  // other offset info
  1: bool doc_level,

  // if xpath is not empty, then annotation applies to an offset
  // within data that starts with an XPATH query into XHTML or XML
  2: string xpath,

  // see above
  3: OffsetType type,

  // actual offset, which could be measured in bytes, chars, or lines
  4: i64 start,
  5: i64 end,
}

/**
 * labels are human generated assertions about data.  For example, a
 * human author might label their own text by inserting hyperlinks to
 * Wikipedia, or a NIST assessor might record judgments about a TREC
 * document.
 */
struct Label {
  // target_kb is a knowledge base of topics or entities used to
  // define the labels, e.g. http://en.wikipedia.org/wiki/ 
  1: string target_kb

  // moment in history to freeze the source
  2: optional StreamTime snapshot_time,

  // string identifying the labeling target
  3: string target_id,

  // a numerical score with meaning that depends on the label.source
  // and the annotation.source
  4: optional i16 relevance,

  // another numerical score that is generally orthogonal to relevance
  // and also depends on the label.source and the annotation.source
  5: optional i16 confidence,
}

/**
 * used in StreamItem as an array of assertions made about the data
 */
struct Annotation {
  // a string describing the source, e.g. 'NIST TREC Assessor' or
  // 'Author Inserted Hyperlink'
  1: string source,

  // moment when annotation judgmnet was rendered by human
  2: StreamTime stream_time,

  // class instance hierarchy path to the data to which this labeling
  // applies.  This string will contain "." symbols, which imply
  // levels in the class instance hierarchy, e.g. 'body.html' means
  // stream_item.body.html
  3: string path,

  4: Offset offset,

  5: Label label,
}

/**
 * This is the primary interface to the corpus data.  It is called
 * StreamItem rather than CorpusItem and has a required StreamTime
 * attribute, because even for a static corpus, each document was
 * captured at a particular time in Earth history and might have been
 * different if captured earlier or later.  All corpora are stream
 * corpora, even if they were not explicitly created as such.
 *
 * stream_id is the unique identifier for documents in the corpus.
 * 
 */
struct StreamItem {
  // md5 hash of the abs_url
  1: string doc_id,  

  // normalized form of the original_url
  2: binary abs_url, 

  // scheme://hostname parsed from abs_url
  3: string schost,  

  // the original URL string obtain from some source
  4: binary original_url, 

  // string uniquely identifying this data set, generally should
  // include a year string
  5: string source,  

  // might be obtained separately from the body
  6: ContentItem title,  

  // primary content
  7: ContentItem body,   

  // A single anchor text of a URL pointing to this doc.  Note that
  // this does not have metadata like the URL of the page that
  // contained this anchor.  Such general link graph data may
  // eventually motivate an extension to this thrift definition.
  8: ContentItem anchor, 

  // see above
  9: SourceMetadata source_metadata, 

  // stream_id is actual unique identifier for the corpus,
  // stream_id = '%d-%s' % (int(stream_time.epoch_ticks), doc_id)
  10: string stream_id,  
  11: StreamTime stream_time,

  // array of annotation objects for the document
  12: optional list<Annotation> annotation
}
