import json
import requests
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

# Configuration depuis ton .env
ACCESS_TOKEN = "EAASMyPXjg7wBReALUWCs2I7rErB86sbpdx0PoGbfXgpXNygSiW1CeeJYxC21YnBHZBZCzt5CAZCSKZAE6zFGRlshiDVQAkc0Y5htCzajnwZAFcJnsYlezTagQhwjkWWtTFZBJbNYtoNrEGWOieSxL0CPE89ZA3dv1n065zdyQyFrxMB2OXJojibAyRTUh1O5wZDZD"
PHONE_ID = "1075918528938252"
VERIFY_TOKEN = "fegg_test_2024"

@csrf_exempt
def whatsapp_webhook(request):
    # 1. Validation de l'URL par Meta (GET)
    if request.method == 'GET':
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            return HttpResponse(challenge)
        return HttpResponse("Erreur de jeton", status=403)

    # 2. Réception et réponse automatique (POST)
    if request.method == 'POST':
        data = json.loads(request.body)
        try:
            # On récupère le message et le numéro du client
            entry = data['entry'][0]['changes'][0]['value']
            if 'messages' in entry:
                message = entry['messages'][0]
                client_phone = message['from']
                text_received = message['text']['body'].lower()

                # LOGIQUE DU BOT : Réponse selon le mot-clé
                if "prix" in text_received or "produit" in text_received:
                    send_whatsapp_message(client_phone, "Bonjour ! Voici nos tarifs actuels pour Salmon Store : \n- Produit A : 5000 FCFA\n- Produit B : 7000 FCFA.\nQue souhaitez-vous commander ?")
                else:
                    send_whatsapp_message(client_phone, "Bienvenue chez Salmon Store ! Tapez 'PRIX' pour voir notre catalogue.")
        except Exception as e:
            print(f"Erreur : {e}")
            
        return JsonResponse({"status": "ok"})

def send_whatsapp_message(to_phone, message_text):
    url = f"https://graph.facebook.com/v19.0/{PHONE_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": message_text}
    }
    requests.post(url, json=payload, headers=headers)