import string
import random
import nltk # 3.4.1
from rake_nltk import Rake # 1.0.4
from nltk.tokenize.treebank import TreebankWordDetokenizer as TWD
from nltk.corpus import stopwords

# install nltk dependencies
nltk.download("averaged_perceptron_tagger")
nltk.download("punkt")
nltk.download("stopwords")

class Document:
    def __init__(self, raw_string):
        """
        raw_string - string of a document
        Constructor for document, creates a document containing sentences
        """

        self._raw_string = raw_string
        raw_sentences = nltk.sent_tokenize(self._raw_string)
        self._sentences = [Sentence(sentence) for sentence in raw_sentences]

    def format_questions(self):
        """
        Turns questions into form suitable for server
        Returns List of tuples in form (question, answer)
        """

        questions = self._get_questions()
        # turn into list of tuples
        tuples = list(questions.items())

        return tuples

    def _get_questions(self):
        """
        Returns a dictionary of questions containing on question
            from each sentence
        Returns dict of form {word: question}
        """

        questions = dict()
        for sentence in self._sentences:
            all_questions = sentence.get_questions()
            if len(all_questions) > 0:
                # choose one question from all the questions
                random_question = random.choice(list(all_questions.items()))
                # turn into dict
                dict_random_question = dict([random_question])
                # add to questions to return
                questions.update(dict_random_question)

        return questions

    def __str__(self):
        """
        Returns original document raw string
        """

        return self._raw_string

class Sentence:
    def __init__(self, raw_string):
        """
        raw_string - string of a single sentence
        Constructor for sentence, creates one sentence with questions
        """

        self._raw_string = raw_string
        self._words = nltk.word_tokenize(self._raw_string)

        # preprocess possible keywords and possible questions
        # for quicker runtime access
        self._preprocess_keywords()
        self._preprocess_questions()

    def get_questions(self):
        """
        Gets all questions for sentence
        Returns dict of form {word: question}
        """

        return self._questions

    def _preprocess_questions(self):
        """
        Preprocesses clean words to create blanked questions
            using all clean words
        """

        self._questions = dict()

        # all possible words that can be used as answers
        clean_words = [word.lower() for word in self._words if self._is_clean(word)]
        dt = TWD()

        for word in clean_words:
            # use lowercase for better equality check
            lower_words = [word.lower() for word in self._words]
            # don't use lower_words to preserve capitalization
            words_copy = self._words.copy()
            # put a blank in place of the word
            for index in [index for index, value in enumerate(lower_words) if value == word]:
                words_copy[index] = "_____"

            self._questions[word] = dt.detokenize(words_copy)

    def _is_clean(self, word):
        """
        word - full case word
        Applies rules to determine if word is good
        Returns true if word is usable, false otherwise
        """

        word_pos = nltk.pos_tag([word])[0][1]

        # check if its a keyword
        if not word.lower() in self._keywords:
            return False

        # normal ascii, no punctuation
        for char in word:
            if not char in string.printable:
                return False
            if char in string.punctuation:
                return False

        CURRENT = ["JJ", "JJR", "JJS", "NN", "NNS", "NNP", "NNPS"]
        # adj and noun only
        if not word_pos in CURRENT:
            return False
        
        # removes words like "use" (NN), but allows abbreviations
        if ((word_pos == "NN" or word_pos == "JJ") and len(word) <= 4) or (word_pos == "NNS" and len(word) <= 5):
            if word.islower() or word[:1].isupper() and word[1:].islower():
                return False

        # removes small unimportant words
        if word in stopwords.words("english"):
            return False

        return True

    def _preprocess_keywords(self):
        """
        Preprocesses RAKE keywords to be used in
            question preprocessing
        Keywords will be all lowercase
        """

        r = Rake(max_length = 1)
        r.extract_keywords_from_text(self._raw_string)
        self._keywords = r.get_ranked_phrases()

    def __str__(self):
        """
        Returns original sentence raw string
        """

        return self._raw_string