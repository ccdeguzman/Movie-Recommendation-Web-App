import pandas as pd
import numpy as np
import difflib
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from flask import Flask, render_template, request, jsonify
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# API from TMDB configuration
TMDB_API_KEY = os.environ.get('TMDB_API_KEY', "API_KEY_HERE")
TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMG_BASE_URL = "https://image.tmdb.org/t/p/w500"

# Load and prepare dataset
df = pd.read_csv("movies_dataset.csv")

# Select features for recommendation
features = ['keywords', 'cast', 'genres', 'director']

# Removing all NaN in features by filling it with an empty string
for feature in features:
    df[feature] = df[feature].fillna("")

# Combine_features
def combine_features(row):
    return row["keywords"] + " " + row["cast"] + " " + row["genres"] + " " + row["director"]

df["combine_features"] = df.apply(combine_features, axis=1)

# Create count matrix and compute cosine similarity
cv = CountVectorizer()
count_matrix = cv.fit_transform(df["combine_features"])
cosine_sim = cosine_similarity(count_matrix)

# Building a dictionary for movie titles
title_to_index = {}
for i, t in enumerate(df["title"].astype(str)):
    lower_title = t.lower()
    title_to_index[lower_title] = i
 
# Helper functions
def get_title_from_index(index):
    return df[df.index == index]["title"].values[0]

def get_details_from_index(index):
    movie = df[df.index == index].iloc[0]
    return {
        'title': movie['title'],
        'overview': movie['overview'],
        'release_date': movie['release_date'],
        'vote_average': float(movie['vote_average']),
        'genres': movie['genres'],
        'director': movie['director']
    }

def get_tmdb_movie_data(movie_title, year=None):
    """
    Fetching movie data from API
    """
    try:
        url_search = f"{TMDB_BASE_URL}/search/movie"
        params = {
            'api_key': TMDB_API_KEY,
            'query': movie_title
        }
        if year:
            params['year'] = year
        
        response = requests.get(url_search, params=params)
        data = response.json()
        
        if data['results']:
            movie = data['results'][0]
            
            #If available
            if movie.get('poster_path'):
                poster_path = f"{TMDB_IMG_BASE_URL}{movie['poster_path']}"
            else:
                poster_path = None
                
            if movie.get('backdrop_path'):
                backdrop_path = f"{TMDB_IMG_BASE_URL}{movie['backdrop_path']}"
            else:
                backdrop_path = None
            
            result = {
                'poster_path': poster_path ,
                'backdrop_path': backdrop_path,
                'tmdb_id': movie['id']
            }
            
            return result
        
    except Exception as e:
        print(f"Error fetching TMDB data: {e}")
        return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/search', methods=['POST'])
def search_movies():
    """
    Searching movies by title
    """
    data = request.json
    query = data.get('query', '').strip().lower()
    
    if not query:
        return jsonify({'error': 'No query'}), 400
    
    # Looking for close matches
    title_list = list(title_to_index.keys())
    suggestions = difflib.get_close_matches(query, title_list, n=10, cutoff=0.4)
    
    results = []
    for suggestion in suggestions:
        index = title_to_index[suggestion]
        movie_details = get_details_from_index(index)
        
        # Extracting year from release date
        year = None
        if movie_details['release_date']:
            year = movie_details['release_date'].split('-')[0]
        
        # Getting TMDB data
        tmdb_data = get_tmdb_movie_data(movie_details['title'], year)
        
        poster_path = 'static/placeholder.png'
        if tmdb_data and 'poster_path' in tmdb_data:
            poster_path = tmdb_data['poster_path']
        
        results.append({
            'index': int(index),
            'title': movie_details['title'],
            'year': year,
            'poster': poster_path
        })
    return jsonify({"results": results})

@app.route('/api/recommend', methods=['POST'])
def recommend():
    """
    Getting movie recommendations
    """
    data = request.json
    movie_index = data.get('movie_index')
    
    if movie_index is None:
        return jsonify({'error': 'No movie index provided'}), 400
    try:
        movie_index = int(movie_index)
        
        # Getting the selected movie details
        selected_movie = get_details_from_index(movie_index)
        release_date = selected_movie.get('release_date')
        if release_date:
            year = release_date.split('-')[0]
        else:
            year = None

        tmdb_data = get_tmdb_movie_data(selected_movie['title'], year)
        
        selected_movie_info = {}
        
        selected_movie_info['title'] = selected_movie['title']
        selected_movie_info['overview'] = selected_movie['overview']
        selected_movie_info['year'] = year
        selected_movie_info['rating'] = selected_movie['vote_average']
        selected_movie_info['genres'] = selected_movie['genres']
        selected_movie_info['director'] = selected_movie['director']
        
        if tmdb_data:
            selected_movie_info['poster'] = tmdb_data.get('poster_path')
            selected_movie_info['backdrop'] = tmdb_data.get('backdrop_path')
        else:
            selected_movie_info['poster_path'] = None
            selected_movie_info['backdrop_path'] = None
        
        # Getting similar movies
        sim_movies = list(enumerate(cosine_sim[movie_index]))
        sorted_sim_movies = sorted(sim_movies, key=lambda x: x[1], reverse=True)
        
        # Top 10 recommendation 
        recommendations = []
        for movie in sorted_sim_movies[1:12]:
            rec_index = movie[0]
            similarity_score = movie[1]
            
            rec_details = get_details_from_index(rec_index)
            release_date = rec_details.get('release_date')
            if release_date:
                rec_year = release_date.split('-')[0]
            else:
                rec_year = None
            
            rec_tmdb_data = get_tmdb_movie_data(rec_details['title'], rec_year)
            
            # Checking poster image path
            if rec_tmdb_data and 'poster_path' in rec_tmdb_data:
                poster_path = rec_tmdb_data['poster_path']
            else:
                poster_path = '/static/placeholder.png'
            
            recommendation = {
                'index': int(rec_index),
                'title': rec_details['title'],
                'overview': rec_details['overview'],
                'year': rec_year,
                'rating': rec_details['vote_average'],
                'similarity': float(similarity_score),
                'poster': poster_path
            }
            
            recommendations.append(recommendation)
        return jsonify({
            'selected_movie': selected_movie_info,
            'recommendations': recommendations
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/random', methods=['GET'])
def random_movies():
    """
    Getting random popular movies for homepage
    """
    try:
        popular_movies = df[df['vote_count'] > 100].sample(n=min(20, len(df)))
        
        results = []
        for i, movie in popular_movies.iterrows():
            release_date = movie.get('release_date')
            if release_date:        
                year = movie['release_date'].split('-')[0]
            else:
                year = None
            
            tmdb_data = get_tmdb_movie_data(movie['title'], year)
            
            if tmdb_data and 'poster_path' in tmdb_data:
                poster_path = tmdb_data['poster_path']
            else:
                poster_path = '/static/placeholder.png'
            
            # Building dictionary
            movie_info = {
                'index': int(movie['index']),
                'title': movie['title'],
                'year': year,
                'rating': float(movie['vote_average']),
                'poster': poster_path
            }
            results.append(movie_info)
            return jsonify({'movies': results})
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
if __name__ == "__main__":
    app.run(debug=True, port=5000)