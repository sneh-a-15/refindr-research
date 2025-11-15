#!/usr/bin/env python3
"""
NLTK Setup Script for ReFindr
Run this script to download required NLTK resources
"""

import nltk
import os
import sys

def download_nltk_resources():
    """Download required NLTK resources"""
    
    # List of required NLTK resources
    resources = [
        'punkt',
        'punkt_tab',
        'stopwords',
        'wordnet',
        'averaged_perceptron_tagger',
        'vader_lexicon'
    ]
    
    print("Downloading NLTK resources...")
    print("-" * 50)
    
    for resource in resources:
        try:
            print(f"Downloading {resource}...")
            nltk.download(resource, quiet=False)
            print(f"✓ {resource} downloaded successfully")
        except Exception as e:
            print(f"✗ Failed to download {resource}: {e}")
    
    print("-" * 50)
    print("NLTK setup complete!")
    
    # Verify punkt_tab is available
    try:
        nltk.data.find('tokenizers/punkt_tab')
        print("✓ punkt_tab tokenizer verified")
    except LookupError:
        print("✗ punkt_tab tokenizer still not found")
        print("Try running: python -c \"import nltk; nltk.download('punkt_tab', force=True)\"")

def create_nltk_data_directory():
    """Create NLTK data directory if it doesn't exist"""
    nltk_data_path = os.path.expanduser('~/nltk_data')
    if not os.path.exists(nltk_data_path):
        os.makedirs(nltk_data_path)
        print(f"Created NLTK data directory: {nltk_data_path}")

if __name__ == "__main__":
    print("ReFindr NLTK Setup")
    print("=" * 50)
    
    # Create data directory
    create_nltk_data_directory()
    
    # Download resources
    download_nltk_resources()
    
    print("\nSetup completed! You can now run your Django application.")