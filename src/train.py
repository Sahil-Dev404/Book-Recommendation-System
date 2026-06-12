"""
train.py — Run this ONCE to train and save the recommender model.
Usage: python train.py
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from model.nlp_pipeline import BookRecommender

def train():
    data_path  = os.path.join('data', 'Books_Cleaned.csv')
    model_path = os.path.join('model', 'recommender.pkl')

    if not os.path.exists(data_path):
        print(f"ERROR: Dataset not found at {data_path}")
        sys.exit(1)

    recommender = BookRecommender()
    recommender.load_and_prepare_data(data_path)

    # Quick sanity check
    result = recommender.recommend("Harry Potter and the Philosopher's Stone", top_n=3)
    if 'error' not in result:
        print("\nSanity check passed! Top recommendation:")
        print(" →", result['recommendations'][0]['title'])
    else:
        print("Sanity check warning:", result['error'])

    recommender.save_model(model_path)
    print("\nTraining complete. Run `python app.py` to start the server.")

if __name__ == '__main__':
    train()
