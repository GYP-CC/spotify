from flask import Flask, request
from spotipy.oauth2 import SpotifyOAuth
import spotipy
import os

SPOTIFY_CLIENT_ID = 'x'
SPOTIFY_CLIENT_SECRET = 'x'
SPOTIFY_SCOPE = 'playlist-read-private playlist-read-collaborative user-library-read user-read-private'
REDIRECT_URI = 'https://ef1c-101-235-253-205.ngrok-free.app/callback'  # 使用你 ngrok 给的地址

CACHE_PATH = os.path.join(os.path.dirname(__file__), '.spotify_token.json')
app = Flask(__name__)
sp_oauth = SpotifyOAuth(
    client_id=SPOTIFY_CLIENT_ID,
    client_secret=SPOTIFY_CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=SPOTIFY_SCOPE,
    cache_path=CACHE_PATH
)
print(25, CACHE_PATH)

@app.route('/')
def login():
    auth_url = sp_oauth.get_authorize_url()
    return f'<a href="{auth_url}">点击授权 Spotify</a>'

@app.route('/callback')
def callback():
    code = request.args.get('code')
    token_info = sp_oauth.get_access_token(code)
    sp = spotipy.Spotify(auth=token_info['access_token'])
    current_user = sp.current_user()
    return f"✅ 授权成功！你好，{current_user['display_name']}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8888)

