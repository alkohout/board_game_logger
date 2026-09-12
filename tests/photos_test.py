"""Photos of a sitting: upload, view, delete — and never someone else's."""
import os, sys, io, struct, zlib
sys.path.insert(0, '/home/kohoutal/projects/board_game_logger')
os.chdir('/home/kohoutal/projects/board_game_logger')
from dotenv import dotenv_values
SUPER_PW = dotenv_values('.env').get('PASSWORD', '')
os.environ.update(SECRET_KEY='k', DB_USER='bgl_app', PASSWORD='local-test-pw',
                  ANTHROPIC_API_KEY='stub')
import psycopg2, flask_web_interface as f
f.app.secret_key = 'k'

ok = fail = 0
def check(label, got, want):
    global ok, fail
    good = got == want
    ok, fail = ok + good, fail + (not good)
    print(f'  {"ok  " if good else "FAIL"} {label}: {got}' + ('' if good else f'  (expected {want})'))

def png(width=4, height=4):
    """A real, tiny PNG — enough that the server sees genuine image bytes."""
    raw = b''.join(b'\x00' + b'\xff\x00\x00' * width for _ in range(height))
    def chunk(tag, data):
        c = tag + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c))
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
            + chunk(b'IDAT', zlib.compress(raw))
            + chunk(b'IEND', b''))

su = psycopg2.connect(host='localhost', database='boardgames', user='postgres', password=SUPER_PW)
k = su.cursor()
from werkzeug.security import generate_password_hash
PW = generate_password_hash('pw-for-tests')
k.execute("UPDATE users SET password_hash=%s WHERE is_owner", (PW,))
k.execute("DELETE FROM login_attempts")
k.execute("DELETE FROM game_photos WHERE game_id IN (SELECT id FROM games WHERE game_title LIKE 'ZZph%')")
k.execute("DELETE FROM games WHERE game_title LIKE 'ZZph%'")
k.execute("DELETE FROM users WHERE email LIKE 'zz-ph%'")
su.commit()
c = f.app.test_client()
H = {'Authorization': 'Bearer ' + c.post('/api/login',
     json={'email': 'owner@example.com', 'password': 'pw-for-tests'}).get_json()['token']}

def upload(game_id, blob, mime='image/png', headers=None, name='photo.png'):
    return c.post(f'/api/games/{game_id}/photo', headers=headers or H,
                  data={'photo': (io.BytesIO(blob), name, mime)},
                  content_type='multipart/form-data')

print('LOGGING A PLAY HANDS BACK ITS ID')
r = c.post('/api/add_game', headers=H, json={
    'date_played': '2026-09-01', 'game_title': 'ZZph Mid Game',
    'notes': 'Bots turn'}).get_json()
check('logged', r.get('success'), True)
check('  and returns the id to hang a photo on', isinstance(r.get('id'), int), True)
gid = r['id']

print('\nATTACHING A PHOTO')
img = png()
r = upload(gid, img).get_json()
check('uploaded', r.get('success'), True)
check('  size recorded', r.get('bytes'), len(img))
pid = r['id']
d = c.get(f'/api/games/{gid}/photos', headers=H).get_json()
check('listed against the play', [p['id'] for p in d['photos']], [pid])
check('  without dragging the bytes through the listing',
      'image' in d['photos'][0], False)
check('  but saying how big it is', d['photos'][0]['bytes'], len(img))

print('\nFETCHING IT BACK')
r = c.get(f'/api/photos/{pid}', headers=H)
check('served', r.status_code, 200)
check('  as an image', r.headers['Content-Type'], 'image/png')
check('  byte-for-byte', r.get_data(), img)
check('  and privately cached', 'private' in r.headers.get('Cache-Control', ''), True)
check('a stranger with no token gets nothing', c.get(f'/api/photos/{pid}').status_code, 401)

print('\nWHAT IT REFUSES')
check('no file', c.post(f'/api/games/{gid}/photo', headers=H,
      data={}, content_type='multipart/form-data').status_code, 400)
check('a PDF is not a photo',
      upload(gid, b'%PDF-1.4 not an image', 'application/pdf', name='x.pdf').status_code, 400)
check('an empty file', upload(gid, b'').status_code, 400)
big = b'\x89PNG\r\n\x1a\n' + b'\x00' * (f.PHOTO_MAX_BYTES + 10)
check('one that is too big', upload(gid, big).status_code, 413)
check('  and nothing was stored for it',
      len(c.get(f'/api/games/{gid}/photos', headers=H).get_json()['photos']), 1)
check('a play that does not exist', upload(99999999, img).status_code, 404)

print('\nGAME INFO CARRIES IT')
gi = c.get('/api/game_info?term=ZZph Mid Game', headers=H).get_json()
check('the last play lists its photos', [p['id'] for p in gi['last']['photos']], [pid])

print('\nANOTHER ACCOUNT CANNOT SEE OR TOUCH IT')
k.execute("""INSERT INTO users (email, password_hash, status, is_owner, display_name)
             VALUES ('zz-ph@test.com',%s,'active',false,'ph') RETURNING id""", (PW,))
other = k.fetchone()[0]; su.commit()
H2 = {'Authorization': 'Bearer ' + c.post('/api/login',
      json={'email': 'zz-ph@test.com', 'password': 'pw-for-tests'}).get_json()['token']}
check('cannot fetch the image', c.get(f'/api/photos/{pid}', headers=H2).status_code, 404)
check('cannot list it', c.get(f'/api/games/{gid}/photos', headers=H2).get_json()['photos'], [])
check('cannot delete it', c.delete(f'/api/photos/{pid}', headers=H2).status_code, 404)
k.execute("SELECT count(*) FROM game_photos WHERE id=%s", (pid,))
check('  and it survives', k.fetchone()[0], 1)
check('cannot attach one to your play', upload(gid, img, headers=H2).status_code, 404)
check('  nor via game_info', c.get('/api/game_info?term=ZZph', headers=H2).status_code, 404)

print('\nSEVERAL PHOTOS ON ONE SITTING')
second = upload(gid, png(6, 6)).get_json()['id']
d = c.get(f'/api/games/{gid}/photos', headers=H).get_json()
check('both listed, oldest first', [p['id'] for p in d['photos']], [pid, second])

print('\nDELETING')
check('removed', c.delete(f'/api/photos/{second}', headers=H).get_json()['success'], True)
check('  gone from the list',
      [p['id'] for p in c.get(f'/api/games/{gid}/photos', headers=H).get_json()['photos']], [pid])
check('  and gone for good', c.get(f'/api/photos/{second}', headers=H).status_code, 404)
check('deleting it twice is a 404, not a crash',
      c.delete(f'/api/photos/{second}', headers=H).status_code, 404)

print('\nDELETING THE ACCOUNT TAKES ITS PHOTOS')
check('game_photos is in the owned list', 'game_photos' in f.USER_OWNED_TABLES, True)
k.execute("INSERT INTO games (user_id, date_played, game_title) VALUES (%s,'2026-09-02','ZZph Theirs') RETURNING id", (other,))
their_game = k.fetchone()[0]
k.execute("""INSERT INTO game_photos (user_id, game_id, image, mime, byte_size)
             VALUES (%s,%s,%s,'image/png',%s)""", (other, their_game, psycopg2.Binary(img), len(img)))
su.commit()
c.delete(f'/api/users/{other}', headers=H)
k.execute("SELECT count(*) FROM game_photos WHERE user_id=%s", (other,))
check('  no orphaned photos left behind', k.fetchone()[0], 0)
k.execute("SELECT count(*) FROM game_photos WHERE id=%s", (pid,))
check('  and yours is untouched', k.fetchone()[0], 1)

print('\nTHE PAGE')
page = open('docs/dashboard.html').read()
api = open('docs/api.js').read()
check('the log form can take a picture', 'capture="environment"' in page, True)
check('  shrunk before it is sent', 'function shrinkImage' in api, True)
check('  because a phone shot is far bigger than needed', 'PHOTO_MAX_EDGE = 1600' in api, True)
# 1600px is fine for "where was I" and useless for reading a board: a track
# number comes out about five pixels tall. Reference shots get their own size.
check('a larger size exists for reading small print',
      'PHOTO_DETAIL_EDGE = 3600' in api, True)
check('  and is not then ruined by compression',
      'quality = Math.max(quality, 0.92)' in api, True)
check('  offered when logging', 'id="photo-detail"' in page, True)
check('  and when adding to an existing play', 'id="gi-detail"' in page, True)
check('a full-detail shot still fits the upload limit',
      f.PHOTO_MAX_BYTES >= 6 * 1024 * 1024, True)
check('images are fetched with the token, not a bare src',
      'function apiImageUrl' in api, True)
check('  and blob urls are released when a photo goes',
      'revokeObjectURL' in api, True)
check('game info shows them', 'id="gi-shots"' in page, True)
check('  and can add one to an existing play', 'id="gi-photo"' in page, True)
check('tapping opens it full size', 'id="shot-viewer"' in page, True)
check('  escape closes it', "e.key === 'Escape'" in page, True)

k.execute("DELETE FROM game_photos WHERE game_id IN (SELECT id FROM games WHERE game_title LIKE 'ZZph%')")
k.execute("DELETE FROM games WHERE game_title LIKE 'ZZph%'")
k.execute("DELETE FROM users WHERE email LIKE 'zz-ph%'")
su.commit(); k.close(); su.close()
print(f'\n{ok} passed, {fail} failed')
