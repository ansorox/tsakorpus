import os
import re
import json
import gzip
from simple_convertors.text_processor import TextProcessor


class Txt2JSON:
    """
    Contains methods to make JSONs ready for indexing from
    raw text files, a csv with metadata and a list with parsed
    word forms.
    """

    rxStripDir = re.compile('^.*[/\\\\]')
    rxStripExt = re.compile('\\.[^.]*$')

    def __init__(self, settingsDir='conf'):
        """
        Load settings, including corpus name and directory, from the
        corpus.json file in settings directory. Then load all other
        settings from the corpus directory. These may override the
        initially loaded settings.
        """
        self.settingsDir = settingsDir
        self.corpusSettings = {}
        self.load_settings()
        self.corpusSettings['corpus_dir'] = os.path.join(self.corpusSettings['corpus_dir'],
                                                         self.corpusSettings['corpus_name'])
        self.settingsDir = os.path.join(self.corpusSettings['corpus_dir'],
                                        'conf')
        self.load_settings()

        fCategories = open(os.path.join(self.settingsDir, 'categories.json'), 'r',
                           encoding='utf-8-sig')
        self.categories = json.loads(fCategories.read())
        fCategories.close()
        self.meta = {}
        self.tp = TextProcessor(settings=self.corpusSettings,
                                categories=self.categories)

    def load_settings(self):
        fCorpus = open(os.path.join(self.settingsDir, 'corpus.json'), 'r',
                       encoding='utf-8-sig')
        self.corpusSettings.update(json.loads(fCorpus.read()))
        if self.corpusSettings['json_indent'] < 0:
            self.corpusSettings['json_indent'] = None
        fCorpus.close()

    def load_meta(self):
        """
        Load the metainformation about the files of the corpus
        from the tab-delimited meta file.
        """
        self.meta = {}
        fMeta = open(os.path.join(self.corpusSettings['corpus_dir'],
                                  self.corpusSettings['meta_filename']),
                     'r', encoding='utf-8-sig')
        for line in fMeta:
            if len(line) <= 3:
                continue
            metaValues = line.split('\t')
            curMetaDict = {}
            for i in range(len(self.corpusSettings['meta_fields'])):
                fieldName = self.corpusSettings['meta_fields'][i]
                if i >= len(metaValues):
                    break
                if fieldName == 'filename':
                    if not self.corpusSettings['meta_files_case_sensitive']:
                        metaValues[i] = metaValues[i].lower()
                    self.meta[metaValues[i]] = curMetaDict
                else:
                    curMetaDict[fieldName] = metaValues[i].strip()
        fMeta.close()

    def convert_file(self, fnameSrc, fnameTarget):
        if fnameSrc == fnameTarget:
            return 0, 0, 0

        fname2check = fnameSrc
        curMeta = {'filename': fnameSrc}
        if not self.corpusSettings['meta_files_dir']:
            fname2check = self.rxStripDir.sub('', fname2check)
        if not self.corpusSettings['meta_files_ext']:
            fname2check = self.rxStripExt.sub('', fname2check)
        if not self.corpusSettings['meta_files_case_sensitive']:
            fname2check = fname2check.lower()
        if fname2check not in self.meta:
            print('File not in meta:', fnameSrc)
        else:
            curMeta.update(self.meta[fname2check])
        textJSON = {'meta': curMeta, 'sentences': []}
        fSrc = open(fnameSrc, 'r', encoding='utf-8')
        text = fSrc.read()
        fSrc.close()

        textJSON['sentences'], nTokens, nWords, nAnalyze = self.tp.process_string(text)

        if self.corpusSettings['gzip']:
            fTarget = gzip.open(fnameTarget, 'wt', encoding='utf-8')
        else:
            fTarget = open(fnameTarget, 'w', encoding='utf-8')
        json.dump(textJSON, fp=fTarget, ensure_ascii=False,
                  indent=self.corpusSettings['json_indent'])
        fTarget.close()
        return nTokens, nWords, nAnalyze

    def process_corpus(self):
        """
        Take every text file from the source directory subtree, turn it
        into a parsed json and store it in the target directory.
        """
        if self.corpusSettings is None or len(self.corpusSettings) <= 0:
            return
        self.load_meta()
        nTokens, nWords, nAnalyzed = 0, 0, 0
        srcDir = os.path.join(self.corpusSettings['corpus_dir'], 'txt')
        targetDir = os.path.join(self.corpusSettings['corpus_dir'], 'json')
        for path, dirs, files in os.walk(srcDir):
            for filename in files:
                if not filename.lower().endswith('.txt'):
                    continue
                targetPath = path.replace(srcDir, targetDir)
                if targetPath == path:
                    continue    # this should never happen, but just in case
                if not os.path.exists(targetPath):
                    os.makedirs(targetPath)
                fnameSrc = os.path.join(path, filename)
                fnameTarget = os.path.join(targetPath, filename)
                fextTarget = '.json'
                if self.corpusSettings['gzip']:
                    fextTarget = '.json.gz'
                fnameTarget = self.rxStripExt.sub(fextTarget, fnameTarget)
                curTokens, curWords, curAnalyzed = self.convert_file(fnameSrc, fnameTarget)
                nTokens += curTokens
                nWords += curWords
                nAnalyzed += curAnalyzed
        print('Conversion finished.', nTokens, 'tokens total,', nWords, 'words total.')
        if nWords > 0:
            print(nAnalyzed, 'words parsed (' + str(nAnalyzed / nWords * 100) + '%).')


if __name__ == '__main__':
    t2j = Txt2JSON()
    t2j.process_corpus()