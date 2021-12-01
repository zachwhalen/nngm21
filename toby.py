import requests
import spacy
spacy.load('en_core_web_lg')
import re
from bs4 import BeautifulSoup
!pip install weasyprint==52.5
from weasyprint import HTML, CSS
from weasyprint.fonts import FontConfiguration

# remove gutenberg header and footer
def clean_book(book):
  b = book.encode('iso-8859-1').decode()
  by_lines = b.split('\r\n')
  start = 0
  end = 0
  # Find the beginning and end of the actual text
  for i in range(len(by_lines)):
    if (by_lines[i].find("*** START OF ") > -1):
      start = i
    if (by_lines[i].find("*** END OF ") > -1):
      end = i
  return " ".join(by_lines[start + 1:end - 1])

# check for all caps
def is_all_caps(word):
  for l in range(len(word)):
    if (word[l] != word[l].upper()):
      return False
  return True

# for sorting names by length so I can the long ones first.
def name_sort(x):
  return len(x[0])

# download Treasure Island
book_url = "https://www.gutenberg.org/files/120/120-0.txt"
r = requests.get(book_url)

# this seems to fix some issues with punctuation marks
book = clean_book(r.text)

# load spacy's nlp object and parse the book
nlp = spacy.load("en_core_web_lg", disable=["parser"])
# doc = nlp(book)

# remove line breaks
lb = re.compile("\r\n")
tx = re.sub(lb," ",book)
doc = nlp(tx)

# Use named entity recognition to get a list of all the named people
names = ["Treasure"]
for ent in doc.ents:
  if (ent.label_ is "PERSON"):
    names.append(ent.text)

# do some work to figure out how to replace all the Tobys
k = []
for n in list(set(names)):
  # ignore some things that are likely not to be names
  if (n[0] is not "1" and 
      n[1] is not "." and 
      n[1] is not " " and
      n[0] == n[0].upper()):
    name = n.replace("--","")
    tp = []

    # some special replacements
    for np in name.split():
      if (is_all_caps(np)):
        tp.append("TOBY")
      elif(np[0] != np[0].upper()):
        tp.append(np)
      elif(np[-2:] == "’s"):
        tp.append("Toby’s")
      else:
        tp.append("Toby")
   
    # save all the names and their respective toby's as a list tuples
    k.append((name, " ".join(tp)))

# sort that list to put the longer ones first
k.sort(key=name_sort,reverse=True)


# download the HTML version to work with that formatting
html_book_url = "https://www.gutenberg.org/cache/epub/120/pg120-images.html"
r_html = requests.get(html_book_url)

# soupify
soup = BeautifulSoup(r_html.text, 'html.parser')

# strip out the header and footer
soup.select("pre:nth-of-type(1)")[0].decompose()
soup.find_all("pre")[-1].decompose()
soup.find_all("style")[-1].decompose()

# remove links
for a in soup.select("a"):
  del a['href']

# remove a few other tags that don't help
for es in soup.select("a.c3 "):
  es.decompose()
for me in soup.find_all("meta"):
  me.decompose()
for li in soup.find_all("link"):
  li.decompose()

for im in soup.find_all("img"):
  im['src'] = "https://www.gutenberg.org/cache/epub/120/" + im['src']

# finally, do the replacing here

soup_string = str(soup)
for toby in k:
  pattern = re.compile(r"" + toby[0] + "")
  soup_string = re.sub(pattern,toby[1],soup_string)

# prepare WeasyPrint
font_config = FontConfiguration()
rendered_html = HTML(string=soup_string)

css = CSS(string='''
@import url('https://fonts.googleapis.com/css2?family=Merriweather:wght@300&display=swap');
body {
font-family: 'Merriweather', serif;
background: white !important;
}

/*hr {
  break-after: recto; 
}*/

h1 {
  font-size: 50pt;
  text-align:center;
  margin-top: 3in;
 
}
h2{
  break-before: recto;
  
}

/*h5 {

  break-after: recto;
}*/

h3 {
  font-size: 20pt;
  text-align:center;
}

/* set the basic page geometry and start the incrementer */
@page {
  font-family: 'Merriweather', serif;
  margin: 1in;
  size: letter;
  counter-increment: page;
  @bottom-center {
    content: "Toby Island";
    text-align:center;
    font-style: italic;
    color: #666666;
  }
}

/* print the page number on the bottom-right of recto pages */
@page :right {
  @bottom-right{
    content: "[" counter(page) "]";
    text-align:right;
    color: #666666;
    visibility: invisible;
  }
}

/* print the page number on the bottom-left of verso pages */
@page :left {
  @bottom-left{
    content: "[" counter(page) "]";
    text-align:left;
    color: #666666;
  }
}

/* blank the footer on the first page */
@page:first{
  @bottom-left {content: ""}
  @bottom-right {content: ""}
  @bottom-center {content: ""}
}


''', font_config=font_config)

rendered_html.write_pdf('/content/toby-island.pdf', stylesheets=[css],font_config=font_config)
