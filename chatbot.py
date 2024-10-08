import os
import json
import random
import string
import numpy as np
import pickle
import nltk
from tensorflow.keras.preprocessing.sequence import pad_sequences
from keras.models import load_model
from nltk.stem import WordNetLemmatizer

# Initialize global variables
responses = {}
lemmatizer = None
tokenizer = None
le = None
model = None
input_shape = None
project_directory = os.path.abspath(os.path.dirname(__file__))

# Load response dataset
def load_response():
    global responses
    responses = {}
    file_path = os.path.join(project_directory, 'model_chatbot', 'dataset.json')
    with open(file_path, encoding='utf-8') as file:
        data = json.load(file)
    for intent in data['intents']:
        responses[intent['tag']] = intent['responses']

# Preparation function
def preparation():
    global lemmatizer, tokenizer, le, model, input_shape
    load_response()

    # Load tokenizer and lemmatizer
    file_path = os.path.join(project_directory, 'model_chatbot', 'tokenizer.pkl')
    with open(file_path, 'rb') as f:
        tokenizer = pickle.load(f)

    le_path = os.path.join(project_directory, 'model_chatbot', 'le.pkl')
    with open(le_path, 'rb') as f:
        le = pickle.load(f)  # Memuat objek LabelEncoder yang telah disimpan
    model_path = os.path.join(project_directory, 'model_chatbot', 'chat_model_new.h5')
    model = load_model(model_path)

    lemmatizer = WordNetLemmatizer()
    input_shape = len(tokenizer)  # Set input shape sesuai dengan jumlah kata yang digunakan

    nltk.download('punkt', quiet=True)
    nltk.download('wordnet', quiet=True)
    nltk.download('omw-1.4', quiet=True)

# Function to remove punctuation
def remove_punctuation(text):
    return ''.join([char.lower() for char in text if char not in string.punctuation])

# Function to convert text to vector
def vectorization(text):
    if tokenizer is None:
        raise ValueError("Tokenizer is not initialized. Call preparation() first.")
    
    text = remove_punctuation(text)
    word_patterns = nltk.word_tokenize(text)
    word_patterns = [lemmatizer.lemmatize(word.lower()) for word in word_patterns]
    
    vector = [1 if word in word_patterns else 0 for word in tokenizer]
    
    # Sesuaikan panjang vektor menjadi sesuai dengan panjang yang diharapkan oleh model
    vector = pad_sequences([vector], maxlen=input_shape)
    return vector

# Function to predict response tag
def predict(vector):
    if model is None:
        raise ValueError("Model is not initialized. Call preparation() first.")
    
    output = model.predict(vector)
    output = output.argmax()
    response_tag = le.inverse_transform([output])[0]
    return response_tag

# Function to generate response
def generate_response(text):
    if not all(v is not None for v in [tokenizer, model, le]):
        raise ValueError("Tokenizer, model, or label encoder is not initialized. Call preparation() first.")
    
    vector = vectorization(text)
    response_tag = predict(vector)
    answer = random.choice(responses[response_tag])
    return answer

# Call preparation to initialize all global variables
preparation()
