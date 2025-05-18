# main.py
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import json
import requests
import time
import os
from bs4 import BeautifulSoup
import re
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed

SPOTIFY_CLIENT_ID = 'x'
SPOTIFY_CLIENT_SECRET = 'x'
SPOTIFY_REDIRECT_URI = 'https://ef1c-101-235-253-205.ngrok-free.app/callback'


GENIUS_ACCESS_TOKEN = '8nPzTWxLn4T'

CACHE_PATH = os.path.join(os.path.dirname(__file__), '.spotify_token.json')

sp_oauth = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=SPOTIFY_REDIRECT_URI,
    scope='playlist-read-private playlist-read-collaborative user-library-read user-read-private',
    cache_path=CACHE_PATH
)

token_info = sp_oauth.get_cached_token()
if token_info:
    access_token = token_info['access_token']
    expires_at = token_info['expires_at']
    if expires_at and expires_at < time.time():
        print("Token 已过期，正在刷新...")
        token_info = sp_oauth.refresh_access_token(token_info['refresh_token'])
        access_token = token_info['access_token']
        print(f"新的 Access Token: {access_token}")
    else:
        print(f"当前 Access Token: {access_token}")
else:
    print("没有找到缓存的 token，请进行授权流程")

if not token_info:
    print("⚠️ 尚未授权，请先运行 app.py 进行授权。")
    exit()

access_token = token_info['access_token']
sp = spotipy.Spotify(auth=access_token)

def search_genius_lyrics_url(song_title, artist_name):
    base_url = 'https://api.genius.com/search'
    headers = {'Authorization': f'Bearer {GENIUS_ACCESS_TOKEN}'}
    params = {'q': f'{song_title} {artist_name}'}
    response = requests.get(base_url, headers=headers, params=params)
    if response.status_code == 200:
        hits = response.json()['response']['hits']
        if hits:
            return hits[0]['result']['url']
    return None

def get_genius_lyrics(song_title, artist_name):
    base_url = 'https://api.genius.com/search'
    headers = {'Authorization': f'Bearer {GENIUS_ACCESS_TOKEN}'}

    clean_title = re.sub(r'\(.*?\)', '', song_title).strip()
    params = {'q': f'{clean_title} {artist_name}'}

    search_response = requests.get(base_url, headers=headers, params=params)
    if search_response.status_code != 200:
        return None

    hits = search_response.json().get('response', {}).get('hits', [])
    if not hits:
        return None

    song_url = None
    for hit in hits:
        hit_title = hit['result']['title'].lower()
        hit_artist = hit['result']['primary_artist']['name'].lower()
        if clean_title.lower() in hit_title and artist_name.lower() in hit_artist:
            song_url = hit['result']['url']
            break
    if not song_url:
        song_url = hits[0]['result']['url']

    page = requests.get(song_url)
    if page.status_code != 200:
        return None

    soup = BeautifulSoup(page.text, 'html.parser')
    lyrics_divs = soup.find_all('div', attrs={'data-lyrics-container': 'true'})
    if not lyrics_divs:
        return None

    raw_lyrics = "\n".join([div.get_text(separator="\n").strip() for div in lyrics_divs])

    def clean_lyrics_text(text):
        lines = text.splitlines()
        cleaned_lines = []
        start_collecting = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
            if not start_collecting and re.match(r"\[.*?\]", line):
                start_collecting = True
            if start_collecting:
                cleaned_lines.append(line)
        return "\n".join(cleaned_lines)

    return clean_lyrics_text(raw_lyrics)


def get_all_tracks_by_artist(sp, artist_id):
    tracks = []
    seen_track_ids = set()

    albums = sp.artist_albums(artist_id, album_type='album,single', limit=50)
    album_ids = list({album['id'] for album in albums['items']})

    for album_id in album_ids:
        album_tracks = sp.album_tracks(album_id)
        for track in album_tracks['items']:
            if track['id'] not in seen_track_ids:
                tracks.append(track)
                seen_track_ids.add(track['id'])

    return tracks
def process_track(track, artist_name):
    name = track['name']
    
    try:
        full_track = sp.track(track['id'])
        
        popularity = full_track.get('popularity', None)
        
        image_url = None
        images = full_track.get('album', {}).get('images', [])
        if images:
            image_url = images[0]['url']
            
        url = search_genius_lyrics_url(name, artist_name)
        lyrics = get_genius_lyrics(name, artist_name)

        status = 'ok' if lyrics else 'no_lyrics'
        return {
            'spotify': track,
            'popularity': popularity, 
            'image_url': image_url,
            'genius_url': url,
            'lyrics': lyrics,
            # 'audio_features': audio_features,
            'status': status
        }
    except Exception as e:
        print(f'⚠️ 抓取失败: {name} - {artist_name}，错误: {e}')
        return {
            'spotify': track,
            'popularity': None, 
            'image_url': None,
            'genius_url': None,
            'lyrics': None,
            # 'audio_features': None,
            'status': f'error: {str(e)}'
        }


def main():
    
    artist_names = ['','','','','','','','','','','']
    for artist_name in artist_names:
        results = sp.search(q=artist_name, type='artist', limit=1)
        items = results['artists']['items']
        if not items:
            print(f"❌ 没找到艺人：{artist_name}")
            continue

        artist = items[0]
        artist_id = artist['id']
        all_tracks = get_all_tracks_by_artist(sp, artist_id)
       
        result_data = []
        safe_name = artist_name.replace('/', '_').replace('\\', '_')
        output_file = f'{safe_name}_top_tracks.json'
        temp_file = tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.json')

        with ThreadPoolExecutor(max_workers=10) as executor:
            future_to_track = {
                executor.submit(process_track, track, artist_name): track
                for track in all_tracks
            }
        for idx, future in enumerate(as_completed(future_to_track), start=1):
                result = future.result()
                name = result['spotify']['name']
                print(f'🎵 [{idx}/{len(all_tracks)}] {name} - {artist_name} ({result["status"]})')
                result_data.append(result)
                
                temp_file.seek(0)
                json.dump(result_data, temp_file, ensure_ascii=False, indent=2)
                temp_file.flush()

        temp_file.close()
        os.replace(temp_file.name, output_file)
        print(f'✅ 已完成：{artist_name}，写入到 {output_file}')

if __name__ == '__main__':
    main()