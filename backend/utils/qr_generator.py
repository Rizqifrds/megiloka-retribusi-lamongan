import hmac
import hashlib
import base64
import os
import io
import qrcode
from PIL import Image

def generate_qr_security_hash(ticket_code, destination_id, valid_date_str, secret_key):
    """
    Menghasilkan signature HMAC-SHA256 untuk memvalidasi keaslian tiket QR Code MegiLoka
    """
    raw_message = f"{ticket_code}|{destination_id}|{valid_date_str}".encode('utf-8')
    signature = hmac.new(secret_key.encode('utf-8'), raw_message, hashlib.sha256).hexdigest()
    return signature[:16] # Short secure hash signature

def create_ticket_qr_payload(ticket_code, destination_id, valid_date_str, secret_key):
    """
    Format Payload QR Code:
    MGLK|{TICKET_CODE}|{DESTINATION_ID}|{VALID_DATE}|{SEC_HASH}
    """
    sec_hash = generate_qr_security_hash(ticket_code, destination_id, valid_date_str, secret_key)
    payload = f"MGLK|{ticket_code}|{destination_id}|{valid_date_str}|{sec_hash}"
    return payload, sec_hash

def verify_qr_payload(payload_str, secret_key):
    """
    Mendekode & Memverifikasi payload QR Code dari scanner gate
    Return: (is_valid, ticket_code, destination_id, valid_date_str, error_message)
    """
    parts = payload_str.strip().split('|')
    if len(parts) != 5 or parts[0] != 'MGLK':
        # Fallback jika hanya input kode tiket murni (misal: manual typing di loket)
        if len(parts) == 1 and parts[0].startswith('MGLK-'):
            return True, parts[0], None, None, None
        return False, None, None, None, "Format QR Code tidak valid atau bukan Tiket Resmi MegiLoka."
    
    _, ticket_code, destination_id, valid_date_str, expected_hash = parts
    calculated_hash = generate_qr_security_hash(ticket_code, destination_id, valid_date_str, secret_key)
    
    if not hmac.compare_digest(expected_hash, calculated_hash):
        return False, ticket_code, destination_id, valid_date_str, "Tanda tangan digital (HMAC Hash) tidak cocok. Indikasi tiket palsu!"
    
    return True, ticket_code, destination_id, valid_date_str, None

def generate_qr_image_base64(payload_str):
    """
    Menghasilkan gambar QR Code dalam format Data URI Base64 untuk tampilan web instan
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(payload_str)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#005B94", back_color="white") # MegiLoka Blue Theme
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
    return f"data:image/png;base64,{img_str}"

def save_qr_image_file(payload_str, output_path):
    """
    Menyimpan file QR Code PNG ke direktori static server
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=8,
        border=3,
    )
    qr.add_data(payload_str)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#005B94", back_color="white")
    img.save(output_path)
    return output_path
