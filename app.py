from flask import Flask, render_template, request, jsonify
import requests
import os
import base64
import random
from dotenv import load_dotenv

# 1. Setup
load_dotenv()
app = Flask(__name__)

# --- CONFIGURATION ---
HF_API_KEY = os.getenv("HF_API_KEY")

# ⚠️ NEW FIXED URL (Hugging Face moved their API)
# We use the new 'router' endpoint for Flux Schnell
HF_API_URL = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"
HF_HEADERS = {"Authorization": f"Bearer {HF_API_KEY}"}

# Fallback URL (Pollinations)
POLLINATIONS_URL = "https://image.pollinations.ai/prompt/"

def generate_with_huggingface_flux(prompt):
    """Primary: Hugging Face FLUX (New Router URL)"""
    print(f"🛕 Trying Hugging Face (Flux) for: '{prompt}'")
    payload = {"inputs": prompt}
    
    response = requests.post(HF_API_URL, headers=HF_HEADERS, json=payload)
    
    # 403 means you haven't accepted terms on the HF website
    if response.status_code == 403:
        raise Exception("HF 403: Please accept the license at https://huggingface.co/black-forest-labs/FLUX.1-schnell")
    
    # 503 means model is loading (common for free tier)
    if response.status_code == 503:
        raise Exception("HF 503: Model is loading, switching to fallback.")

    if response.status_code != 200:
        raise Exception(f"HF Error {response.status_code}: {response.text}")
        
    return response.content

def generate_with_pollinations(prompt):
    """Fallback: Pollinations (Flux)"""
    print(f"🏹 Fallback to Pollinations for: '{prompt}'")
    encoded_prompt = requests.utils.quote(prompt)
    seed = random.randint(1, 99999)
    # Ensuring we use Flux model here too
    url = f"{POLLINATIONS_URL}{encoded_prompt}?width=1024&height=1024&model=flux&nologo=true&seed={seed}"
    
    response = requests.get(url)
    if response.status_code != 200:
        raise Exception(f"Pollinations Error: {response.status_code}")
        
    return response.content

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/generate', methods=['POST'])
def generate_image():
    data = request.json
    prompt = data.get('prompt', '')
    
    if not prompt:
        return jsonify({"error": "The scroll is empty. Speak your vision."}), 400

    image_bytes = None
    used_service = "Hugging Face (Flux)"

    try:
        # 1. Try Primary (Hugging Face)
        image_bytes = generate_with_huggingface_flux(prompt)
    except Exception as e:
        print(f"⚠️ Primary Failed: {e}")
        try:
            # 2. Try Fallback (Pollinations)
            used_service = "Pollinations (Fallback)"
            image_bytes = generate_with_pollinations(prompt)
        except Exception as e2:
            return jsonify({"error": "The spirits are silent (Both APIs failed)."}), 500

    # 3. Return Image
    base64_img = base64.b64encode(image_bytes).decode('utf-8')
    img_data_url = f"data:image/jpeg;base64,{base64_img}"

    return jsonify({
        "image_data": img_data_url, 
        "service": used_service,
        "status": "success"
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
