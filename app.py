'''
using Flask as the backdend
    GET ->serve index.html
    POST/recommend ->return book recommendations(JSON)
    GET ->return title suggestions(JSON)
    GET/health ->health check for render
'''
import os
import pickle
import sys
from flask import Flask, request, jsonify, render_template
from src.nlp_pipeline import BookRecommender

app=Flask(__name__)

# loading the model

MODEL_PATH=os.path.join('model','recommender.pkl')
recommender=BookRecommender()

def load_model():
    if not os.path.exists(MODEL_PATH):
        print("model not found")
        from train import train
        train()
    recommender.load_model(MODEL_PATH)
    print("recommender ready")

load_model()

#routes

@app.route('/') #the frontend by html
def index():
    return render_template('index.html')


@app.route('/recommend', methods=['POST'])
def recommend():
    data = request.get_json()
    if not data or 'title' not in data:
        return jsonify({'error': 'Please provide a book title.'}), 400

    title  = data['title'].strip()
    top_n  = int(data.get('top_n', 8))

    if not title:
        return jsonify({'error': 'Title cannot be empty.'}), 400

    result = recommender.recommend(title, top_n=top_n)
    return jsonify(result)


@app.route('/autocomplete')
def autocomplete():
    query = request.args.get('q', '').strip()
    if len(query) < 2:
        return jsonify([])
    suggestions = recommender.get_suggestions(query, n=7)
    return jsonify(suggestions)


@app.route('/health') #as iam deploying on the render , the load-balancers need to know if app is actually running or it it has frozen , they will ping the health endpoint every few seconds. if it returns 200ok, they keep sending user traffic to it .
def health():
    return jsonify({'status': 'ok', 'books_loaded': len(recommender.df)}), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    app.run(host='0.0.0.0', port=port, debug=True)