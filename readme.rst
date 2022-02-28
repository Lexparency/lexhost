Lexparency.org's legislative act hosting service
================================================
A web application for uploading, searching, and reading legislative
acts.

Prerequisites
-------------
 - Python version 3.7.2 (or later)
 - virtualenv or a Python installation with the packages from the
   requirements.txt installed.
 - Elasticsearch (version 7.X) should be running on the local machine under
   port 9200

Setup
-----
This app ships with a bash setup script. Just do as follows:

  1) open a bash command shell,
  2) change to this app's directory
  3) run the command

     $ bash scripts/bash/setup.sh

     and follow the instructions.


Basic API
=========

Content navigation
------------------

The navigation through the hosted content happens vai the web application, which
are all provided via GET requests. The URL paths have the following structure:

/<legislative domain>/<local ID>/<fragment>/<version>

Where

   1) "legislative domain" identifies the legislative corpus of the requested
      content, e.g. "eu" for legislative acts of the European Union
   2) "local ID" is the identifier of the legislative act within the corpus of
      the considered legislative domain.
   3) "fragment" identifies the requested part of the legislative act, identified
      by legislative domain and local ID. These fragments are the leaves of the
      nested tree-structure of the legislative act. E.g. Articles for the case
      EU-Law.
      A special value for the fragment sub-path is "TOC". In this case, an
      overview page (TOC -> Table Of Contents) is provided, displaying the
      nested structure of container and articles (leaves of the contents table),
      as well as an overview of the document's meta data.
   4) "version" indicates the requested version of the legal act, taking into
      account that those documents are subject to change. The conventions for
      version labels may differ for each legislative domain.
      A special value for the version sub-path is "latest" indicating that the
      latest available version is being requested.


Searching
---------

   1) Path and query string for searching the corpus of a legislative domain:

      /<legislative domain>/search?search_words=<search words>[&<filter field>=<filter value>]

      where various filter fields can be chosen.
   2) Path and query string for searching the content of a legislative act

      /<legislative domain>/<local ID>/search?search_words=<search words>


Uploading
---------

The legislative acts need to be transformed into a specific format, in order to
be uploaded (posted) to this document hosting service. The format specifications
are inspired by Akoma-Ntoso, but are not equal to it and unfortunately, are not
documented yet. However, by considering the examples 32002R0006.html,
32009L0065.html, 32013R0575.html, and 32016R0679.html under legislative_act/tests/data/.
The RDFa data in these examples is mostly inspired by the ELI ontology. However,
in some cases it is simplified: E.g. for the "is_about" predicate, the RDFa data
directly provides the corresponding expressions in the relevant language instead
of pointing to the abstract EuroVoc resource.

Uploading these documents happens via a POST request, with the following path:
    /<legislative domain>/
The data is expected to be an HTML document complying the format specification.

Posting a document could be done via the command line tool "curl":

curl -XPOST localhost:5000/eu/32013R0575/initial/ -H "Content-type: text/html; charset=UTF-8" -d @32013R0575.html

where 32013R0575.html is the file with the document to be uploaded. Also, this
bundle ships with a bash script that wraps this curl command. It can be found
under: scripts/bash. Usage:

post_doc.sh /<legislative_domain>/ <path to file>


View Model for the Lexparency interface
=======================================


Landing page
------------
...

Article
-------
The Article view needs to provide the following information:

1) Which document am I currently reading
   A typical EU legal act has various forms for identification:

     a) CELEX
        Official Document identification system used by the EU, e.g.: 320132015
        A very technical form of identification. Currently, this identifier is used
        in Lexparency's URLs. This identifier should not be shown within the Article view
        since the typical reader is not even aware of this identifier system.
     b) Expert reference (Human readable ID)
        Examples: Regulation (EU) 2013/575, Directive 2013/63/EU
     c) Popular name
        Examples:

           - Banana Regulation
           - Medical Devices Regulation
           - Capital Requirements Directive

        Only the important Documents feature a popular name.
        This identifier should be provided, when available
     d) Popular Acronym
        Examples: CRR, CRD, MiFID II
        Only the important Documents feature a popular name.
        This identifier should be provided, when available.
        Note that the existence of a popular name does not imply the existence of a popular acronym.

3) Legal status
   Is the present legal act currently in force or is it outdated.
   If it is outdated, provide a link to the repealing document.
4) Current version / existing versions
   Each listed available versions can have the status:

     - available /
5) Where am I with respect to the current document:

    - represented via the document's contents table (Chapter hierarchy)
      This information can be hidden on the mobile version of the view.
    - Naming the current Article.


Search Results
--------------
The search results view should inform about:

1) The used search words
2) The applied filter
   This includes the possibility of a search within a single document.
3) The current page of the search results
4) For a database search, each search hit should contain:

   a) Locator:
       - Document identification (possibly including popular names and abbreviations)
       - Article or Annex ordinate, e.g. Article 10
   b) Legal status (In-force / outdated)
   c) Snippet phrases from the proposed Article

5) For a document search, each search hit schould contain:



Contents Table
--------------
...

Padding pages (About page and similar)
--------------------------------------
...
