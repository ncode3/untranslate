import azure.functions as func
import logging
import requests
import json
import os

# Create a FunctionApp instance (Python v2 model)
app = func.FunctionApp()

@app.function_name("translate")
@app.route(route="translate", auth_level=func.AuthLevel.FUNCTION)
def translate_text(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')

    # Parse JSON POST body
    try:
        req_body = req.get_json()
        text = req_body.get('text')
        source_language = req_body.get('sourceLanguage', '')
        target_language = req_body.get('targetLanguage', 'en')
        use_strict_mode = req_body.get('useStrictMode', False)
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid request body"}),
            status_code=400,
            mimetype="application/json"
        )

    # Validate input
    if not text:
        return func.HttpResponse(
            json.dumps({"error": "Please provide text to translate"}),
            status_code=400,
            mimetype="application/json"
        )

    # Get environment variables
    translator_key = os.environ.get('TRANSLATOR_KEY')
    translator_endpoint = os.environ.get('TRANSLATOR_ENDPOINT')
    logging.info(f"Using endpoint: {translator_endpoint}")

    if not translator_key or not translator_endpoint:
        return func.HttpResponse(
            json.dumps({"error": "Translator configuration missing"}),
            status_code=500,
            mimetype="application/json"
        )

    # Construct Translator API call
    translate_url = f"{translator_endpoint.rstrip('/')}/translate"
    params = {
        'api-version': '3.0',
        'to': target_language
    }
    if source_language:
        params['from'] = source_language

    headers = {
        'Ocp-Apim-Subscription-Key': translator_key,
        # Adjust region if your Translator resource is somewhere else (e.g. "eastus2")
        'Ocp-Apim-Subscription-Region': 'eastus',
        'Content-type': 'application/json'
    }
    body = [{'text': text}]

    try:
        logging.info(f"Calling translator API with params: {params}")
        response = requests.post(translate_url, params=params, headers=headers, json=body)
        logging.info(f"Response status code: {response.status_code}")
        logging.info(f"Response content: {response.text}")

        response.raise_for_status()
        translation_result = response.json()

        # Extract the translated text from the JSON response
        translated_text = translation_result[0]['translations'][0]['text']

        # Apply optional UN terminology enforcement
        if use_strict_mode:
            terminology_dict = {
                'Palestine': 'occupied Palestinian territory',
                'فلسطين': 'occupied Palestinian territory',
                'Secretary-General': 'Secretary-General of the United Nations',
                'SG': 'Secretary-General of the United Nations'
            }
            for term, replacement in terminology_dict.items():
                translated_text = translated_text.replace(term, replacement)

        return func.HttpResponse(
            json.dumps({
                "originalText": text,
                "translatedText": translated_text,
                "targetLanguage": target_language,
                "strictModeApplied": use_strict_mode
            }),
            mimetype="application/json"
        )

    except Exception as e:
        logging.error(f"Translation error: {str(e)}")
        return func.HttpResponse(
            json.dumps({"error": f"Translation failed: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )

# -----------------------------------------------------------------
# Diagnostic endpoint to confirm environment variables and test 
# a quick Translator API "languages" call, so you can see logs.
# -----------------------------------------------------------------
@app.function_name("debug")
@app.route(route="debug", auth_level=func.AuthLevel.FUNCTION)
def debug_info(req: func.HttpRequest) -> func.HttpResponse:
    logging.info("Debug endpoint triggered.")

    # Check environment variables
    translator_key = os.environ.get('TRANSLATOR_KEY', 'NOT_SET')
    translator_endpoint = os.environ.get('TRANSLATOR_ENDPOINT', 'NOT_SET')

    # Simple test call to verify the Translator API is accessible
    test_url = f"{translator_endpoint.rstrip('/')}/languages?api-version=3.0"
    headers = {
        'Ocp-Apim-Subscription-Key': translator_key,
        # Adjust this region if needed
        'Ocp-Apim-Subscription-Region': 'eastus',
        'Content-type': 'application/json'
    }

    try:
        r = requests.get(test_url, headers=headers, timeout=10)
        r.raise_for_status()
        translator_ok = True
    except Exception as ex:
        logging.error(f"Test call to Translator failed: {ex}")
        translator_ok = False

    # Truncate key for safety (do not log full credentials in real code)
    partial_key = translator_key[:5] + "*****" if translator_key != 'NOT_SET' else 'NOT_SET'

    debug_report = {
        "translator_key_found": partial_key,
        "translator_endpoint": translator_endpoint,
        "translator_test_call_succeeded": translator_ok
    }

    return func.HttpResponse(
        json.dumps(debug_report),
        status_code=200,
        mimetype="application/json"
    )