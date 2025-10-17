import requests
import pandas as pd
import time
import os
from dotenv import load_dotenv

load_dotenv()

# API from TMDB configuration
TMDB_API_KEY = os.environ.get('TMDB_API_KEY', "API_KEY_HERE")
TMDB_BASE_URL = "https://api.themoviedb.org/3"

def fetch_movies(num_pages = 50):
    """
    Fetching mpopular movies from TMDB
    Each page has 20 movies, 50 pages is 1000 movies
    """
    movies = []
    
    for page in range(1, num_pages + 1):
        print(f"Fetching page {page}/{num_pages}...")
        
        try:
            url=f"{TMDB_BASE_URL}/movie/popular"
            params = {
                'api_key': TMDB_API_KEY,
                'page': page,
                'language': 'en-US'
            }
            response = requests.get(url, params=params)
            data = response.json()
            
            if 'results' in data:
                movies.extend(data['results'])
                
            # 40 requests per 10 seconds
            time.sleep(0.25)
            
        except Exception as e:
            print(f"Error on page {page}: {e}")
            continue
        
    return movies

def fetch_movie_details(movie_id):
    """
    Fetching information for a movie
    """
    try:
        url = f"{TMDB_BASE_URL}/movie/{movie_id}"
        params = {
            'api_key': TMDB_API_KEY,
            'append_to_response' : 'credits, keywords'    
        }
        
        response = requests.get(url, params=params)
        return response.json()
    except Exception as e:
            print(f"Error fetching details for movie {movie_id}: {e}")
            return None
        
def process_movies_to_dataframe(movies):
    """
    Processing movie data and fetching detailed info for each
    """
    data = []
    
    for i, movie in enumerate(movies):
        print(f"Processing movie {i+1}/{len(movies)} : {movie['title']}")
        
        # Fetching info: cast, crew, keywords
        details = fetch_movie_details(movie['id'])
        
        if details:
            # Extracting cast
            cast = []
            if 'credits' in details and 'cast' in details['credits']:
                cast = [actor['name'] for actor in details['credits']['cast'][:5]]

            # Extracting director
            director = ""
            if 'credits' in details and 'crew' in details['credits']:
                for crew_member in details['credits']['crew']:
                    if crew_member['job'] == 'Director':
                        director = crew_member['name']
                        break
            # Extracting genres
            genres = []
            if 'genres' in details:
                genres = [genre['name'] for genre in details['genres']]
            
            # Extract keywords
            keywords = []
            if 'keywords' in details:
                kw_section = details['keywords']
                
                # checking if keyword key is in the section
                if 'keywords' in kw_section:
                    keywords = []
                    for kw in kw_section['keywords']:
                            if 'name' in kw:
                                keywords.append(kw['name'])
            data.append({
                'id': movie['id'],
                'title': movie['title'],
                'original_title': movie.get('original_title', ' '),
                'overview': movie.get('overview', ''),
                'release_date': movie.get('release_date', ''),
                'popularity': movie.get('popularity', 0),
                'vote_average': movie.get('vote_average', 0),
                'vote_count': movie.get('vote_count', 0),
                'original_language': movie.get('original_language', ''),
                'budget': details.get('budget', 0),
                'revenue': details.get('revenue', 0),
                'runtime': details.get('runtime', 0),
                'status': details.get('status', ''),
                'tagline': details.get('tagline', ''),
                'homepage': details.get('homepage', ''),
                'poster_path': movie.get('poster_path', ''),
                'backdrop_path': movie.get('backdrop_path', ''),
                'cast': ' '.join(cast),
                'director': director,
                'genres': ' '.join(genres),
                'keywords': ' '.join(keywords),
            })
            
        time.sleep(0.25)
    return pd.DataFrame(data)

def main():
    print("Starting TMDB data fetch...")
    
    #fectching popular movies
    print("\n Step 1: Fecthing popular movies...")
    movies = fetch_movies(num_pages=50)
    print(f"Fetched {len(movies)} movies")
    
    # Fetching detailed information
    df = process_movies_to_dataframe(movies)
    
    #Saving to CSV
    output_file = 'movies_dataset.csv'
    df.to_csv(output_file, index=False)
    print("\nSample Data:")
    print(df.head())

if __name__ == "__main__":
    main()

