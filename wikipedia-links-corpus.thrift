/**
 * These thrift structures describe the Wikipedia Links Corpus (WLC)
 * which was constructed by fetching the URLs provided by Google here:
 *
 *  http://........
 *
 * After fetching, we performed several processing steps described
 * below.
 */
namespace java wlc
namespace py wlc

/**
 * ContentItem 
 *
 * For the kba-stream-corpus-2012, the specific tag-stripping and NER
 * configurations were:
 *
 *   'raw' --> tika?  or something --> 'converted'  (XX% was non-HTML)
 *   'converted' --> Beautiful Soup parsing lhtml & prettify --> 'html'
 *   'html' --> boilerpipe 1.2.0 ArticleExtractor --> 'cleansed'
 *   'cleansed' -> Stanford CoreNLP ver 1.2.0 with annotators
 *        {tokenize, cleanxml, ssplit, pos, lemma, ner}, property
 *        pos.maxlen=100" --> 'ner'
 *
 *  replace Stanford CoreNLP with FACTORIE?
 */
struct ContentItem {
  1: binary raw, // original download, raw byte array
  2: string encoding, // guessed by ... operating on raw plus headers
  3: optional binary cleansed, // created by ...
  4: optional binary ner, // created by ...
  5: optional binary converted, // created by ...
  6: optional binary html // created by Beautiful Soup prettify
}

/**
 * CorpusItem 
 *
 * 
 */
struct CorpusItem {
  1: string doc_id,  // md5 hash of the abs_url
  2: binary abs_url, // normalized form of the original_url
  3: string schost,  // scheme://hostname parsed from abs_url
  4: binary original_url, // the URL provided in the original data set from Google
  5: string source,  // string identifying this data set, which is always "wikipedia-links-corpus-2012"
  6: ContentItem doc, // see above, unlike other KBA corpora, there is only one ContentItem here
  7: binary headers  // raw bytes of HTTP headers received when fetching a document
}
