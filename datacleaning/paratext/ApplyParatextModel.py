# Gather paratext training data

# This script translates a text file, with pages marked by <pb> tags, 
# into a matrix of features. Features have been selected to permit 
# training a model that distinguishes paratext from body text.
# These functions will be reused in the script that applies the model
# at scale. Model training will happen in a Jupyter notebook.

# We also import training data, which consists of 400+ volumes with pages
# manually tagged to indicate content type. This data is much richer than
# we actually need: it distinguishes indexes from tables of contents, for instance,
# and verse drama from prose drama! For our purposes, we will simplify it to
# just two categories: paratext and body text.

# import modules

import numpy as np
import pandas as pd

import os, math
from collections import Counter

import argparse

top20lexicon = {'you', 'was', 'but', 'my'}
top2000lexicon = set()

# Define the codes that count as paratext.

paratext = {'front', 'title', 'toc', 'impri', 'bookp', 'subsc', 'index', 'back',
             'bibli', 'gloss', 'libra', 'ads'}

paratext_clues = {'v', 'c', 'iv', 'p', 'pp', 'contents', 'd', 'ib', 'illustrations', 'esq', 'cloth',
         'iii', 'vols', 'ii', 'ibid', 'edition', 's', 'vo', 'book', 'volume', 'page', 'shillings',
         'edited', 'chapter', 'author', 'price', 'illustrated', 'extra', 'dollars', 'cents', 'published',
         'library', 'rev', 'crown', 'j', 'v', 'w', 'index', 'vi', 'viii', 'ix', 'x', 'xi', 'xii'}

byofset = {'by', 'of'}
priceset = {'$', '£', '¢'}

with open('/Users/tunder/Dropbox/python/GPT-1914/datacleaning/MainDictionary.txt', encoding = 'utf-8') as file:
    lines = file.readlines()

for i, line in enumerate(lines):
    word = line.split('\t')[0].strip()
    if word in paratext_clues or word in byofset or len(word) < 2:
        continue
    if len(top20lexicon) < 25:
        top20lexicon.add(word)
    if len(top2000lexicon) < 2000: 
        top2000lexicon.add(word)
    else:
        break

verbs = set()
with open('/Users/tunder/Dropbox/python/GPT-1914/datacleaning/englishverbs.txt', encoding = 'utf-8') as file:
    for line in file:
        verbs.add(line.strip())

def paginate_file(filepath):
    ''' This function takes a text file with <pb> tags and returns a list of pages.
    Each page is a list of lines. Each line is a string.
    '''
    with open(filepath, encoding = 'utf-8') as file:
        lines = file.readlines()
    
    pages = []
    current_page = []

    for line in lines:
        if line.startswith('<pb>'):
            pages.append(current_page)
            current_page = []
        else:
            current_page.append(line)
    
    pages.append(current_page)
    return pages

# We construct features in two passes, because many of the final features will be
# relative to volume averages, or to adjacent pages. The first pass calculates
# a set of features that are page-local. The second pass calculates features
# that are relative to the volume or to adjacent pages.

# Initial page-local features:

# pagenum: the (absolute) page number
# pagefrac: the page number divided by the total number of pages
# backnum: the number of pages from the end of the volume
# backfrac: the proportion of the volume that is behind this page
# nlines: the number of lines on the page
# nwords: the number of words on the page
# nalpha: the number of alphabetic characters on the page
# fracalpha: the proportion of alphabetic characters
# nnumeric: the number of numeric characters on the page
# fracnumeric: the proportion of numeric characters
# npunct: the number of punctuation characters on the page
# fracpunct: the proportion of punctuation characters
# nupper: the number of uppercase characters on the page
# fracupper: the proportion of uppercase characters
# nother: the number of characters on the page that are not in the above categories
# fracother: the proportion of characters that are not in the above categories
# meanlinelen: mean linelength (in characters)
# sdlinelen: the standard deviation of linelength (in characters)
# meanwordlength: the mean length of words
# startupper: the proportion of lines that start with an uppercase letter
# top20words: the proportion of words that are in the top 20 most common words
# top2000words: the proportion of words that are in the top 2000 most common words

def page_features(page, pagenum, totalpgcount):
    ''' This function takes a list of lines and returns a dictionary of features.
    '''

    global top20lexicon, top2000lexicon, paratext_clues

    pagefrac = pagenum / totalpgcount
    backnum = totalpgcount - pagenum
    backfrac = backnum / totalpgcount
    nlines = len(page)
    nwords = 0
    nalpha = 0
    nnumeric = 0
    npunct = 0
    nupper = 0
    nother = 0
    nprice = 0
    wordlengths = []
    linelengths = []
    startupper = 0
    top20words = 0
    top2000words = 0
    paratextwords = 0
    byofwords = 0
    
    for line in page:
        nwords += len(line.split())
        linelengths.append(len(line))
        if len(line) == 0:
            pass
        else:
            if line[0].isupper():
                startupper += 1
            for word in line.split():
                wordlengths.append(len(word))
                # strip punctuation and convert to lowercase
                lowerword = ''.join([char.lower() for char in word if char.isalpha()])
                
                if lowerword in byofset:
                    byofwords += 1
                if lowerword in verbs:
                    top20words += 1
                if lowerword in top2000lexicon:
                    top2000words += 1
                if lowerword in paratext_clues:
                    paratextwords += 1
                for char in word:
                    if char.isalpha():
                        nalpha += 1
                    elif char.isnumeric():
                        nnumeric += 1
                    elif char in '.,;:?!()-"“”\'\'':
                        npunct += 1
                    else:
                        nother += 1
                    
                    if char.isupper():
                        nupper += 1
                    if char in priceset:
                        nprice += 1
    
    meanlinelen = np.mean(linelengths) if len(linelengths) > 0 else 0
    sdlinelen = np.std(linelengths) if len(linelengths) > 1 else 0
    meanwordlength = np.mean(wordlengths) if len(wordlengths) > 0 else 0
    nchars = nalpha + nnumeric + npunct + nother + len(wordlengths) # counting words is counting spaces!
    if nchars > 0:
        fracalpha = nalpha / nchars
        fracnumeric = nnumeric / nchars
        fracpunct = npunct / nchars
        fracupper = nupper / nchars
        fracother = nother / nchars
        fracprice = nprice / nchars
    else:
        fracalpha = 1
        fracnumeric = 0
        fracpunct = 0
        fracupper = 0
        fracother = 0
        fracprice = 0
    startupper = startupper / nlines if nlines > 0 else 0
    top20words = top20words / nwords if nwords > 0 else 0
    top2000words = top2000words / nwords if nwords > 0 else 0
    paratextwords = paratextwords / nwords if nwords > 0 else 0
    byofwords = byofwords / nwords if nwords > 0 else 0

    pg_feature_dict = {'pagenum': pagenum, 'pagefrac': pagefrac, 'backnum': backnum, 'backfrac': backfrac,
            'nlines': nlines, 'nwords': nwords, 'nalpha': nalpha, 'fracalpha': fracalpha,
            'nnumeric': nnumeric, 'fracnumeric': fracnumeric, 'npunct': npunct, 'fracpunct': fracpunct,
            'nupper': nupper, 'fracupper': fracupper, 'nother': nother, 'fracother': fracother,
            'meanlinelen': meanlinelen, 'sdlinelen': sdlinelen, 'meanwordlength': meanwordlength,
            'startupper': startupper, 'verbs': top20words, 'top2000words': top2000words, 'paratextwords': paratextwords,
            'byofwords': byofwords, 'fracprice': fracprice}
    return pg_feature_dict

# Now for each page we add the following relative features:

# nwordsminusmean: the number of words on this page minus the volume average
# wordlengthminusmean: the mean word length on this page minus the volume average
# top2000minusmean: the proportion of words on this page that are in the top 2000 minus the volume average
# nwordsminusprev: the number of words on this page minus the number of words on the previous page
# top2000minusprev: the proportion of words on this page that are in the top 2000 minus the proportion on the previous page

def safe_mean(values):
    # Calculate the mean, but return 0 if the list is empty
    return np.mean(values) if values else 0


def add_relative_features(pages, htid):
    '''
    This function accepts a list of dictionaries produced by the page_features function,
    and adds relative features to each dictionary.
    '''

    # We calculate means ignoring zeroes.

    volmeanwords = safe_mean([d['nwords'] for d in pages if d['nwords'] != 0])
    volmeanwordlength = safe_mean([d['meanwordlength'] for d in pages if d['meanwordlength'] != 0])
    volmeantop2000 = safe_mean([d['top2000words'] for d in pages if d['top2000words'] != 0])
    volmeansdlinelen = safe_mean([d['sdlinelen'] for d in pages if d['sdlinelen'] != 0])
    volmeanlinelen = safe_mean([d['meanlinelen'] for d in pages if d['meanlinelen'] != 0])

    for i, page in enumerate(pages):

        # For some features, zero is not an informative value. It tells us only that
        # there are no words on the page, and that's something we already know from
        # the nwords feature. So we replace zero with the volume average, which makes
        # differences in this variable more informative by eliminating the outlier
        # status of pages with no words.

        if page['meanwordlength'] == 0:
            page['meanwordlength'] = volmeanwordlength
        if page['sdlinelen'] == 0:
            page['sdlinelen'] = volmeansdlinelen
        if page['meanlinelen'] == 0:
            page['meanlinelen'] = volmeanlinelen
        if page['top2000words'] == 0:
            page['top2000words'] = volmeantop2000

        # Some features will vary across volumes, but we want to know how they vary
        # within a volume. So we subtract the volume average from the page value.
        # Note that this interacts with the change we made above, replacing zero
        # with the volume average. That's intentional. It means, once again, that pages
        # with no words will tend to have a neutral value for this feature. We already
        # know they have no words, and need to use this feature to make subtler
        # discriminations.

        page['nwordsminusmean'] = page['nwords'] - volmeanwords
        page['wordlengthminusmean'] = page['meanwordlength'] - volmeanwordlength
        page['linelenminusmean'] = page['meanlinelen'] - volmeanlinelen
        page['top2000minusmean'] = page['top2000words'] - volmeantop2000

        # Some features are potentially informative in themselves, but also
        # because a change signals a transition from one part of the volume to another.

        if i > 2:
            nwordsminusprev = page['nwords'] - np.mean([pages[i - 1]['nwords'], pages[i - 2]['nwords'], pages[i - 3]['nwords']])
            top2000minusprev = page['top2000words'] - np.mean([pages[i - 1]['top2000words'], pages[i - 2]['top2000words'], pages[i - 3]['top2000words']])
        elif i > 1:
            nwordsminusprev = page['nwords'] - np.mean([pages[i - 1]['nwords'], pages[i - 2]['nwords']])
            top2000minusprev = page['top2000words'] - np.mean([pages[i - 1]['top2000words'] , pages[i - 2]['top2000words']])
        elif i > 0:
            nwordsminusprev = page['nwords'] - pages[i - 1]['nwords']
            top2000minusprev = page['top2000words'] - pages[i - 1]['top2000words']
        else:
            nwordsminusprev = 0
            top2000minusprev = 0

        page['nwordsminusprev'] = nwordsminusprev
        page['top2000minusprev'] = top2000minusprev

        # We also calculate the absolute distance from the volume's center,
        # and quadratic versions of all positional features.

        page['centerdist'] = abs(page['pagefrac'] - 0.5)
        page['centerdist^2'] = page['centerdist'] ** 2
        page['pagefrac^2'] = page['pagefrac'] ** 2
        page['backfrac^2'] = page['backfrac'] ** 2
        page['htid'] = htid  # we need this to separate training and test sets by volume
    
    # # Check if the mean of relative features is zero
    # mean_wordlengthminusmean = np.mean([d['wordlengthminusmean'] for d in pages])
    # mean_linelenminusmean = np.mean([d['linelenminusmean'] for d in pages])
    # mean_top2000minusmean = np.mean([d['top2000minusmean'] for d in pages])
    # mean_nwordsminusmean = np.mean([d['nwordsminusmean'] for d in pages])

    # print("Mean of wordlengthminusmean:", mean_wordlengthminusmean)
    # print("Mean of linelenminusmean:", mean_linelenminusmean)
    # print("Mean of top2000minusmean:", mean_top2000minusmean)
    # print("Mean of nwordsminusmean:", mean_nwordsminusmean)
    
    return pages

def clean_pairtree(htid):
    period = htid.find('.')
    prefix = htid[0:period]
    postfix = htid[(period+1): ]
    if ':' in postfix:
        postfix = postfix.replace(':','+')
        postfix = postfix.replace('/','=')
    if '.' in postfix:
        postfix = postfix.replace('.',',')
    cleanname = prefix + "." + postfix
    return cleanname

def labeled_volume(htid, textroot):
    '''
    This function takes a volume ID and a root directory for text files. It returns a 
    list of dictionaries, each representing a page, with features and a label.
    '''

    global paratext

    textpath = textroot + htid + '.norm.txt'

    if not os.path.isfile(textpath):
        return []

    pages = paginate_file(textpath)

    totalpgcount = len(pages)

    for i in range(totalpgcount):
        page = page_features(pages[i], i, totalpgcount)
        pages[i] = page
    
    pages = add_relative_features(pages, htid)

    return pages

def main():

    # The valid arguments are
    # -m --meta: the path to the metadata file
    # -f --folder: the path to the folder containing the text files
    # -o --output: the path to the output file

    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--meta", help="the path to the metadata file")
    parser.add_argument("-f", "--folder", help="the path to the folder containing the text files")
    parser.add_argument("-o", "--output", help="the path to the output file")

    args = parser.parse_args()

    if args.meta:
        meta_path = args.meta
    else:
        sys.exit("Please provide the path to the metadata file")
    
    if args.folder:
        folder_path = args.folder
    else:
        sys.exit("Please provide the path to the folder containing the text files")
    
    if args.output:
        output_path = args.output
    else:
        sys.exit("Please provide the path to the output file")

    ctr = 0
    alreadyhave = set()
    
    metadata = pd.read_csv(meta_path, sep = '\t', low_memory = False)

    htids = metadata['htid'].tolist()
    allpages = []

    for htid in htids:

        htid = clean_pairtree(htid)
        
        if htid in alreadyhave:
            continue
        else:
            alreadyhave.add(htid)

        try:
            pages = labeled_volume(htid, folder_path)
            if len(pages) < 1:
                print('Error with', htid)
                continue
        except:
            print('Error with', htid)
            continue
        
        ctr += 1
        if ctr % 20 == 1:
            print(ctr)

        allpages.extend(pages)


    print('Total volumes:', ctr)
    print('Total pages:', len(allpages))

    featurematrix = pd.DataFrame(allpages)
    featurematrix.to_csv(output_path, index = False, sep = '\t')

    volumematrix = featurematrix.groupby('htid').mean().reset_index()
    metadata['htid'] = metadata['htid'].apply(clean_pairtree)
    metadata.set_index('htid', inplace = True)
    volumematrix.set_index('htid', inplace = True)
    volumematrix = volumematrix.merge(metadata[['title', 'inferred_date']], left_index=True, right_index=True, how='inner')
    print('Total volumes after metadata merge:', len(volumematrix))
    volumematrix.drop(['centerdist', 'backfrac', 'nwordsminusmean', 'wordlengthminusmean', 'linelenminusmean', 'top2000minusmean', 
                       'nwordsminusprev', 'centerdist^2', 'pagefrac^2', 'backfrac^2'], axis=1, inplace=True)
    
    featurematrix['n2000words'] = featurematrix['top2000words'] * featurematrix['nwords']
    groups = featurematrix.groupby('htid')
    top10percent2000 = []
    htidindex = []
    for htid, group in groups:
        numrows = len(group)
        if numrows < 1:
            thetop = 0
        else:
            numtoaverage = math.ceil(numrows / 10)
            thetop = np.mean(group.top2000words.sort_values(ascending=False)[0: numtoaverage])
        top10percent2000.append(thetop)
        htidindex.append(htid)
    htid_top10percent2000 = pd.Series(top10percent2000, index = htidindex)
    htid_std_top2000 = featurematrix.groupby('htid')['top2000words'].std()
    htid_sum_top2000 = featurematrix.groupby('htid')['n2000words'].sum()

    htid_features = pd.DataFrame({'max_top2000words': htid_top10percent2000, 'std_top2000words': htid_std_top2000, 'sum_top2000words': htid_sum_top2000})
    htid_features.index.name = 'htid'

    volumematrix = volumematrix.merge(htid_features[['max_top2000words', 'std_top2000words', 'sum_top2000words']], left_index=True, right_index=True, how='inner')

    volumematrix.to_csv(output_path.replace('.tsv', '_volumes.tsv'), sep = '\t')


# Now we have a Counter of word frequencies associated with paratext and with text.
# Let's find words that have at least 50 total occurrences (across both sets),
# and then calculate Dunning's log likelihood for each word.

def dunning(word, corpustext, corpusparatext):
    ''' This function calculates a signed version of
    Dunning's log likelihood for a word.

    Words where the text frequency is higher than the
    paratext frequency will have a positive score.
    Words where the paratext frequency is higher will
    have a negative score.
    '''
    a = corpustext.get(word, 0)
    b = sum(corpustext.values()) - a
    c = corpusparatext.get(word, 0)
    d = sum(corpusparatext.values()) - c

    if a == 0 or b == 0 or c == 0 or d == 0:
        return 0

    # Calculating expected values
    E1 = (a + c) * (a + b) / (a + b + c + d)
    E2 = (a + c) * (c + d) / (a + b + c + d)
    E3 = (b + d) * (a + b) / (a + b + c + d)
    E4 = (b + d) * (c + d) / (a + b + c + d)

    # Log-likelihood calculation
    G2 = 2 * ((a * math.log(a / E1) if a != 0 else 0) +
              (c * math.log(c / E2) if c != 0 else 0) +
              (b * math.log(b / E3) if b != 0 else 0) +
              (d * math.log(d / E4) if d != 0 else 0))

    # Determine the sign
    if a / (a + b) > c / (c + d):
        return G2  # Text frequency is higher, positive score
    else:
        return -G2  # Paratext frequency is higher, negative score
    
def calculate_dunning():
    ''' This function calculates Dunning's log likelihood for each word 
    We create a list of words that occur at least 200 times in the corpus.
    Then we calculate Dunning's log likelihood for each word.
    Not currently used.
    '''

    totalcorpus = corpustext + corpusparatext
    commonwords = [x for x in totalcorpus.keys() if totalcorpus[x] > 200]

    print('Words with more than 200 occurrences:', len(commonwords))

    # Now we calculate Dunning's log likelihood for each word.

    dunninglist = []
    for word in commonwords:
        dunninglist.append((dunning(word, corpustext, corpusparatext), word))

    dunninglist.sort(reverse = True)
    for score, word in dunninglist[0: 40]:
        print(score, word)

    for score, word in dunninglist[-40:]:
        print(score, word)

if __name__ == '__main__':
    main()