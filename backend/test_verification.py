import urllib.request
import json

def verify_system():
    # 1. Verify Homepage
    req = urllib.request.urlopen('http://127.0.0.1:5000/')
    html = req.read().decode('utf-8')
    print('=== VERIFIKASI BERANDA & FITUR ===')
    print('HTTP Status:', req.status)
    print('Spotlight Section Present:', 'spotlightSection' in html)
    print('H-1 Badge Present:', 'H-1 HARI (BESOK!)' in html)
    print('H-30 Badge Present:', '1 BULAN LAGI' in html)
    print('MegiBot AI Widget Present:', 'megibot-panel' in html)
    print('Navbar Notification Bell Present:', 'guestNotifDropdown' in html)
    print('Guest Toast Alert Present:', 'guestAlertToast' in html)
    print('Festival Kupatan in HTML:', 'Festival Kupatan Akbar Tanjung Kodok' in html)
    print('Masjid Namira in HTML:', 'Masjid Namira' in html)
    print('Haul Sunan Drajat in HTML:', 'Haul Akbar' in html)

    # 2. Verify Guest Notifications API
    req_notif = urllib.request.urlopen('http://127.0.0.1:5000/api/guest/notifications')
    notif_data = json.loads(req_notif.read().decode('utf-8'))
    print('\n=== NOTIFIKASI AKTIF UNTUK ROLE GUEST ===')
    print('Total Notifikasi Aktif:', notif_data['total'])
    for idx, n in enumerate(notif_data['notifications']):
        print(f"[{idx+1}] {n['badge_label']} | {n['title']} ({n['days_left']} hari lagi) - {n['location']}")

    # 3. Test AI Customer Service Chat interaction
    post_data = json.dumps({'message': 'Apa saja tempat wisata pantai di Lamongan?'}).encode('utf-8')
    req_ai = urllib.request.Request(
        'http://127.0.0.1:5000/api/ai/chat',
        data=post_data,
        headers={'Content-Type': 'application/json'}
    )
    ai_res = urllib.request.urlopen(req_ai)
    ai_json = json.loads(ai_res.read().decode('utf-8'))
    print('\n=== TEST RESPON AI CS MEGIBOT ===')
    print('Reply preview:\n', ai_json['reply'][:250].encode('ascii', errors='replace').decode('ascii'), '...')

if __name__ == '__main__':
    verify_system()
