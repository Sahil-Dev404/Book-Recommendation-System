import re
import pickle
import pandas as pd
import numpy as np
import nltk
import ssl
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer, PorterStemmer
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# downloading the required nltk resources
def download_nltk_resouces():
    # --- SSL Bypass Snippet Added Here ---
    try:
        _create_unverified_https_context = ssl._create_unverified_context
    except AttributeError:
        pass
    else:
        ssl._create_default_https_context = _create_unverified_https_context
    # -------------------------------------
    
    resources=['punkt','stopwords','wordnet','omw-1.4','punkt_tab']
    for resource in resources:
        try:
            # Removed quiet=True temporarily so you can see if it succeeds
            nltk.download(resource) 
        except Exception as e:
            print(f"Warning: cant download {resource}: {e}")

download_nltk_resouces()


class TextPreprocessor:
    '''cleaning->tokenization->stopword->lemmatization'''

    def __init__(self, use_stemming=False):
        self.lemmatizer=WordNetLemmatizer()
        self.stemmer=PorterStemmer()
        self.stop_words=set(stopwords.words('english'))
        self.use_stemming=use_stemming

    def clean_text(self,text):
        '''remove special char,numbers,extraspaces'''
        if not isinstance(text,str) or text.strip()=='':
            return ''
        text=text.lower()
        text = re.sub(r'[^a-z\s]', ' ', text)   # keep only letters
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def tokenize(self,text):
        return word_tokenize(text)
    
    def remove_stopwords(self,tokens):
        return [t for t in tokens if t not in self.stop_words and len(t)>2]
    
    def lemmatize(self,tokens):
        return [self.lemmatizer.lemmatize(t) for t in tokens]
    
    def stem(self,tokens):
        return [self.stemmer.stem(t) for t in tokens]
    
    def preprocess(self,text):
        '''full pipeline: clean->tokenize->stopwords->lemmatize'''
        text=self.clean_text(text)
        if not text:
            return ''
        tokens=self.tokenize(text)
        tokens=self.remove_stopwords(tokens)
        if self.use_stemming:
            tokens=self.stem(tokens)
        else:
            tokens=self.lemmatize(tokens)
        return ' '.join(tokens)
    
class FeatureBuilder:
    '''it builds the combined feature string from columns'''

    def __init__(self):
        self.preprocessor=TextPreprocessor()

    def safe_str(self,val):
        '''convert any value to string'''
        if pd.isna(val) or val is None:
            return ''
        return str(val)
    
    def build_features(self,row):

        title       = self.safe_str(row.get('title', ''))
        authors     = self.safe_str(row.get('authors', ''))
        genres      = self.safe_str(row.get('genres', ''))
        description = self.safe_str(row.get('description', ''))
        series      = self.safe_str(row.get('series', ''))
        places      = self.safe_str(row.get('places', ''))

        combined = f"{title} {authors} {genres} {genres} {series} {series} {description} {places}"
        return self.preprocessor.preprocess(combined)
    

class BookRecommender:
    '''TF-IDF + cosine similarity'''

    def __init__(self):
        self.df=None
        self.tfidf_matrix=None
        self.vectorizer=None
        self.feature_builder=FeatureBuilder()
        self.preprocessor=TextPreprocessor()

    def load_and_prepare_data(self, csv_path):
        '''load dataset and build tf-idf feature matrix'''
        print('loading dataset')
        self.df=pd.read_csv(csv_path)
        self.df=self.df.drop_duplicates(subset='title').reset_index(drop=True)
        self.df['title_lower']=self.df['title'].str.lower().str.strip()

        print(f"Dataset loaded: {len(self.df)} books")
        print("Building NLP feature vectors...")

        self.df['features']=self.df.apply(self.feature_builder.build_features,axis=1)

        #tf-idf vectorizer
        self.vectorizer=TfidfVectorizer(
            max_features=15000,  #limits the vocabulary to top15,000 most important terms
            ngram_range=(1, 2),     # unigrams + bigrams
            min_df=2,     #ignores word that only appear in only 1 book
            max_df=0.85,  #ignores words appearing in the 85% of books
            sublinear_tf=True       # apply log normalization
        )
        self.tfidf_matrix=self.vectorizer.fit_transform(self.df['features'])
        print(f'tf-idf matrix shape: {self.tfidf_matrix.shape}')
        return self
    
    def find_book_index(self, title):
        """
        Find book index by title (case-insensitive, partial match supported).
        Returns (index, matched_title) or (None, None) if not found.
        """
        query = title.lower().strip()

        # Exact match first
        exact = self.df[self.df['title_lower'] == query]
        if not exact.empty:
            return exact.index[0], self.df.loc[exact.index[0], 'title']

        # Partial match
        partial = self.df[self.df['title_lower'].str.contains(query, na=False)]
        if not partial.empty:
            return partial.index[0], self.df.loc[partial.index[0], 'title']

        return None, None


    def recommend(self, title, top_n=8):
        """
        Recommend books similar to the given title.

        Returns:
            dict with 'query_book' info and list of 'recommendations'
        """
        idx, matched_title = self.find_book_index(title)

        if idx is None:
            return {
                'error': f"Book '{title}' not found in dataset. Try a different title.",
                'suggestions': self.get_suggestions(title)
            }

        # Compute cosine similarity for this book vs all others
        query_vector = self.tfidf_matrix[idx]
        sim_scores = cosine_similarity(query_vector, self.tfidf_matrix).flatten()

        # Sort and exclude the query book itself
        similar_indices = np.argsort(sim_scores)[::-1]
        similar_indices = [i for i in similar_indices if i != idx][:top_n]

        query_book = self.df.iloc[idx]
        recommendations = []

        for i in similar_indices:
            book = self.df.iloc[i]
            recommendations.append({
                'title':            book['title'],
                'authors':          book.get('authors', 'Unknown'),
                'genres':           book.get('genres', ''),
                'rating':           round(float(book.get('rating', 0)), 2),
                'rating_count':     int(book.get('rating_count', 0)),
                'pages':            int(book.get('pages', 0)) if not pd.isna(book.get('pages')) else 0,
                'publish_year':     int(book.get('publish_year', 0)) if not pd.isna(book.get('publish_year')) else 0,
                'series':           book.get('series', ''),
                'similarity_score': round(float(sim_scores[i]), 4),
                'award_count':      int(book.get('award_count', 0)),
                'description':      str(book.get('description', ''))[:250] + '...'
                                    if len(str(book.get('description', ''))) > 250 else str(book.get('description', ''))
            })

        return {
            'query_book': {
                'title':        query_book['title'],
                'authors':      query_book.get('authors', 'Unknown'),
                'genres':       query_book.get('genres', ''),
                'rating':       round(float(query_book.get('rating', 0)), 2),
                'rating_count': int(query_book.get('rating_count', 0)),
                'pages':        int(query_book.get('pages', 0)) if not pd.isna(query_book.get('pages')) else 0,
                'series':       query_book.get('series', ''),
                'award_count':  int(query_book.get('award_count', 0)),
            },
            'recommendations': recommendations
        }

    def get_suggestions(self, query, n=5):
        """Return close title matches for autocomplete / error hints."""
        query = query.lower()
        matches = self.df[self.df['title_lower'].str.contains(query[:4], na=False)]['title'].head(n).tolist()
        return matches

    def save_model(self, path='model/recommender.pkl'):
        """Pickle the trained model."""
        with open(path, 'wb') as f:
            pickle.dump({
                'vectorizer':    self.vectorizer,
                'tfidf_matrix':  self.tfidf_matrix,
                'df':            self.df
            }, f)
        print(f"Model saved to {path}")

    def load_model(self, path='model/recommender.pkl'):
        """Load pickled model."""
        with open(path, 'rb') as f:
            data = pickle.load(f)
        self.vectorizer   = data['vectorizer']
        self.tfidf_matrix = data['tfidf_matrix']
        self.df           = data['df']
        print(f"Model loaded from {path}")
        return self
    
# --- Execution Block Added Here ---
if __name__ == '__main__':
    print("Initializing Recommender System...")
    recommender = BookRecommender()
    
    # Update 'data/raw/books.csv' with your actual dataset filename
    dataset_path = 'data/processed/Books_Cleaned.csv' 
    
    try:
        recommender.load_and_prepare_data(dataset_path)
        recommender.save_model('model/recommender.pkl')
        print("Pipeline execution complete! Model is ready.")
    except FileNotFoundError:
        print(f"\nError: Could not find the file at {dataset_path}")
        print("Please check your file name and update 'dataset_path' in the code above.")